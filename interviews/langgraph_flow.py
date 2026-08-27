import logging
from typing import Any, TypedDict

from django.conf import settings
from langchain_anthropic import ChatAnthropic
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

from .prompts import (
    EVALUATOR_PROMPT,
    MENTOR_PROMPT,
    RESUME_ANALYZER_PROMPT,
    TOPIC_FOLLOWUP_PROMPT,
    TOPIC_OPENING_PROMPT,
)

logger = logging.getLogger(__name__)

ROLE_LABELS = {
    "swe": "Software Engineer",
    "aiml": "AI/ML Engineer",
    "ds": "Data Scientist",
    "app": "App Developer",
    "backend": "Backend Developer",
    "frontend": "Frontend Developer",
    "other": "the selected role",
}

INTRO_QUESTION = (
    "Introduce yourself and walk me through your resume, highlighting what's "
    "most relevant to this role."
)

# The topics the interview digs into after the intro, in order. Each one can take up to
# MAX_FOLLOWUPS_PER_TOPIC follow-up questions if there's still something worth probing.
TOPIC_SEQUENCE = ["skills", "project", "role fit"]
MAX_FOLLOWUPS_PER_TOPIC = 2

# Used only if the LLM call for a topic fails (e.g. missing/invalid API key,
# rate limit, network error), so the interview can still proceed.
FALLBACK_QUESTIONS = {
    "swe": {
        "skills": [
            "Which programming language are you strongest in, and how have you used it beyond coursework?",
            "Explain a data structure or algorithm topic you're confident about, with an example of when you'd use it.",
        ],
        "project": [
            "Pick your most complex project - what was the hardest technical problem in it, and how did you solve it?",
            "If you had another month on one of your projects, what would you add or fix?",
        ],
        "role fit": [
            "What happens when a user enters a URL in the browser and hits enter?",
            "Why do you want to work as a software engineer?",
        ],
    },
    "aiml": {
        "skills": [
            "Which ML library or framework are you most comfortable with, and what have you built with it?",
            "What is overfitting, and how would you reduce it in a model you've trained?",
        ],
        "project": [
            "Walk me through your most involved AI/ML project, from problem statement to result.",
            "What would you change about your ML project's data or model if you redid it today?",
        ],
        "role fit": [
            "How do you evaluate whether a classification model is actually good?",
            "Why are you interested in AI/ML roles specifically?",
        ],
    },
    "ds": {
        "skills": [
            "Which data analysis or visualization tool are you strongest in, and how have you used it?",
            "How would you handle missing or inconsistent values in a dataset you're working with?",
        ],
        "project": [
            "Walk me through a project where you cleaned, analyzed, or visualized real data.",
            "What was the most surprising insight from any data project you've worked on?",
        ],
        "role fit": [
            "What is the difference between correlation and causation, with an example?",
            "Why should we consider you for a data science role?",
        ],
    },
    "app": {
        "skills": [
            "Which mobile/app framework are you most comfortable with, and what have you shipped with it?",
            "How do you manage app state and API calls in something you've built?",
        ],
        "project": [
            "Explain one app you built and the main features you implemented.",
            "What's one performance or UX issue you ran into in an app project, and how did you fix it?",
        ],
        "role fit": [
            "How would you improve app performance and user experience in general?",
            "Why do you want to work as an app developer?",
        ],
    },
    "backend": {
        "skills": [
            "Which backend language or framework are you strongest in, and what did you build with it?",
            "What is the difference between authentication and authorization?",
        ],
        "project": [
            "Explain one backend project and how you designed its database.",
            "What would you change about the architecture of your backend project if you rebuilt it?",
        ],
        "role fit": [
            "How would you design a REST API for a mock interview platform like this one?",
            "Why are you a good fit for backend development?",
        ],
    },
    "frontend": {
        "skills": [
            "Which frontend framework or library are you most comfortable with, and what have you built with it?",
            "What is the difference between client-side and server-side rendering?",
        ],
        "project": [
            "Explain one UI you built and how you made it user-friendly.",
            "What's one accessibility or responsiveness issue you've had to fix in a frontend project?",
        ],
        "role fit": [
            "How would you make a page responsive and accessible in general?",
            "Why should we hire you for a frontend role?",
        ],
    },
    "other": {
        "skills": [
            "What's the technical skill you're most confident about, and how have you applied it?",
            "What are the core skills needed for the role you're targeting?",
        ],
        "project": [
            "Explain one project that is closest to your selected role.",
            "What would you improve about that project if you revisited it today?",
        ],
        "role fit": [
            "Describe a challenge you faced and how you solved it.",
            "Why should we hire you for this role?",
        ],
    },
}


class ResumeSummary(BaseModel):
    summary: str = ""
    skills: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    experience: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weak_areas: list[str] = Field(default_factory=list)


class OpeningQuestion(BaseModel):
    question: str


class FollowupDecision(BaseModel):
    question: str
    moved_on: bool = False


class EvaluationResult(BaseModel):
    score: int = Field(ge=0, le=10)
    feedback: str
    missing_points: list[str] = Field(default_factory=list)
    improved_answer: str = ""


class FinalReportResult(BaseModel):
    summary: str
    strengths: list[str] = Field(default_factory=list)
    weak_areas: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class InterviewState(TypedDict, total=False):
    resume_text: str
    target_role: str
    custom_role: str
    previous_questions: list[str]
    resume_summary: dict[str, Any]
    # This session's questions asked so far: [{"category", "question", "answer", "feedback"}, ...]
    transcript: list[dict[str, Any]]
    topic_index: int
    followups_used: int
    current_question: str
    current_category: str
    interview_complete: bool
    answer_text: str
    evaluations: list[dict[str, Any]]
    user_remarks: str
    final_report: str
    final_report_details: dict[str, Any]


def get_llm(temperature: float = 0.3):
    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=temperature,
        max_tokens=2048,
    )


def analyze_resume(state: InterviewState) -> InterviewState:
    text = state.get("resume_text", "")
    try:
        structured_llm = get_llm(temperature=0.2).with_structured_output(ResumeSummary)
        result = structured_llm.invoke(
            f"{RESUME_ANALYZER_PROMPT}\n\nResume text:\n{text[:6000]}"
        )
        state["resume_summary"] = result.model_dump()
    except Exception:
        logger.exception("Resume analysis LLM call failed; using raw-text fallback")
        state["resume_summary"] = {
            "summary": text[:700],
            "skills": [],
            "projects": [],
            "experience": [],
            "education": [],
            "strengths": [],
            "weak_areas": [],
        }
    return state


def _role_label(state: InterviewState) -> str:
    custom_role = state.get("custom_role", "").strip()
    return custom_role or ROLE_LABELS.get(state.get("target_role", "swe"), "the selected role")


def _shared_context(role_label: str, skills: list[str], projects: list[str], previous_questions: list[str]) -> str:
    return "\n".join(
        [
            f"Target role: {role_label}",
            f"Skills: {', '.join(skills) if skills else 'none listed'}",
            f"Projects: {'; '.join(projects) if projects else 'none listed'}",
            "Previously asked (avoid repeating or rephrasing these): "
            + ("; ".join(previous_questions[-20:]) if previous_questions else "none"),
        ]
    )


def _format_thread(thread: list[dict[str, Any]]) -> str:
    lines = []
    for index, item in enumerate(thread, start=1):
        lines.append(f"Q{index}: {item['question']}")
        lines.append(f"A{index}: {item['answer']}")
        lines.append(f"Feedback{index}: {item['feedback']}")
    return "\n".join(lines)


def _generate_opening_question(
    topic: str, role_label: str, skills: list[str], projects: list[str], previous_questions: list[str]
) -> str:
    context = _shared_context(role_label, skills, projects, previous_questions) + f"\nTopic to open: {topic}"
    structured_llm = get_llm(temperature=0.85).with_structured_output(OpeningQuestion)
    result = structured_llm.invoke(f"{TOPIC_OPENING_PROMPT}\n\n{context}")
    return result.question


def _generate_followup(
    topic: str,
    next_topic: str | None,
    thread: list[dict[str, Any]],
    role_label: str,
    skills: list[str],
    projects: list[str],
    previous_questions: list[str],
) -> FollowupDecision:
    context = (
        _shared_context(role_label, skills, projects, previous_questions)
        + f"\nCurrent topic: {topic}"
        + f"\nNext topic (write its opening question if you decide to move on): {next_topic or 'none - this is the last topic'}"
        + "\nConversation so far on this topic:\n"
        + _format_thread(thread)
    )
    structured_llm = get_llm(temperature=0.85).with_structured_output(FollowupDecision)
    result = structured_llm.invoke(f"{TOPIC_FOLLOWUP_PROMPT}\n\n{context}")
    return result


def _fallback_question(role_key: str, category: str, already_asked: list[str]) -> str:
    bank = FALLBACK_QUESTIONS.get(role_key, FALLBACK_QUESTIONS["other"])[category]
    for question in bank:
        if question not in already_asked:
            return question
    return bank[0]


def generate_next_question(state: InterviewState) -> InterviewState:
    """Decide the next question for this turn: either a deeper follow-up on the
    current topic, or the opening question for the next topic. Called once per
    answer submitted, with `transcript` rebuilt from this session's Q&A so far."""
    role_key = state.get("target_role", "swe")
    role_label = _role_label(state)
    summary = state.get("resume_summary", {})
    skills = summary.get("skills", [])
    projects = summary.get("projects", [])
    transcript = state.get("transcript", [])
    topic_index = state.get("topic_index", 0)
    followups_used = state.get("followups_used", 0)

    all_asked = list(state.get("previous_questions", [])) + [item["question"] for item in transcript]

    if followups_used >= MAX_FOLLOWUPS_PER_TOPIC:
        topic_index += 1
        followups_used = 0

    if topic_index >= len(TOPIC_SEQUENCE):
        state["interview_complete"] = True
        return state

    topic = TOPIC_SEQUENCE[topic_index]
    topic_thread = [item for item in transcript if item["category"] == topic]
    is_fresh_topic = not topic_thread

    try:
        if is_fresh_topic:
            question = _generate_opening_question(topic, role_label, skills, projects, all_asked)
            moved_on = False
        else:
            next_topic = TOPIC_SEQUENCE[topic_index + 1] if topic_index + 1 < len(TOPIC_SEQUENCE) else None
            decision = _generate_followup(topic, next_topic, topic_thread, role_label, skills, projects, all_asked)
            question = decision.question
            moved_on = decision.moved_on
    except Exception:
        logger.exception("Question generation failed for topic=%s", topic)
        question = _fallback_question(role_key, topic, all_asked)
        moved_on = False

    if moved_on:
        topic_index += 1
        followups_used = 0
        if topic_index >= len(TOPIC_SEQUENCE):
            state["interview_complete"] = True
            return state
        topic = TOPIC_SEQUENCE[topic_index]
    elif not is_fresh_topic:
        followups_used += 1

    state["current_question"] = question
    state["current_category"] = topic
    state["topic_index"] = topic_index
    state["followups_used"] = followups_used
    return state


def evaluate_answer(state: InterviewState) -> InterviewState:
    question_text = state.get("current_question", "")
    answer = state.get("answer_text", "").strip()
    evaluations = state.get("evaluations", [])

    if not answer:
        evaluations.append(
            {
                "score": 0,
                "feedback": "No answer was submitted for this question.",
                "missing_points": ["Provide an answer to get feedback."],
                "improved_answer": "",
            }
        )
        state["evaluations"] = evaluations
        return state

    context = (
        f"Target role: {_role_label(state)}\n"
        f"Question asked: {question_text}\n"
        f"Candidate's answer: {answer}"
    )
    try:
        structured_llm = get_llm(temperature=0.3).with_structured_output(EvaluationResult)
        result = structured_llm.invoke(f"{EVALUATOR_PROMPT}\n\n{context}")
        evaluation = result.model_dump()
    except Exception:
        logger.exception("Answer evaluation LLM call failed")
        evaluation = {
            "score": 0,
            "feedback": (
                "Automatic evaluation is temporarily unavailable. Your answer was "
                "saved - try again shortly for real feedback."
            ),
            "missing_points": [],
            "improved_answer": "",
        }
    evaluations.append(evaluation)
    state["evaluations"] = evaluations
    return state


def create_final_report(state: InterviewState) -> InterviewState:
    evaluations = state.get("evaluations", [])
    user_remarks = state.get("user_remarks", "").strip()

    eval_lines = [
        f"Q{index}: score {evaluation.get('score', 0)}/10 - {evaluation.get('feedback', '')}"
        for index, evaluation in enumerate(evaluations, start=1)
    ]
    context = (
        f"Target role: {_role_label(state)}\n"
        f"Per-question evaluations:\n" + ("\n".join(eval_lines) if eval_lines else "none") + "\n"
        f"Candidate's final remarks: {user_remarks or 'none'}"
    )

    try:
        structured_llm = get_llm(temperature=0.4).with_structured_output(FinalReportResult)
        result = structured_llm.invoke(f"{MENTOR_PROMPT}\n\n{context}")
        report = result.model_dump()
    except Exception:
        logger.exception("Final report LLM call failed")
        report = {
            "summary": (
                "Mock interview completed. Automatic report generation is temporarily "
                "unavailable - review your per-question scores and try another mock "
                "interview soon."
            ),
            "strengths": ["Completed all questions"],
            "weak_areas": ["Add more detail and measurable impact in your answers"],
            "recommendations": ["Revise weak technical topics from your interview feedback."],
        }

    state["final_report"] = report["summary"]
    state["final_report_details"] = report
    return state


def build_interview_graph():
    # Only resume analysis runs through the graph at interview start. Every later
    # turn (generate_next_question / evaluate_answer / create_final_report) is
    # called directly per-request from the views, since a human answers between
    # each step - there's no single in-process run to wire as graph edges.
    graph = StateGraph(InterviewState)
    graph.add_node("analyze_resume", analyze_resume)
    graph.set_entry_point("analyze_resume")
    graph.add_edge("analyze_resume", END)
    return graph.compile()
