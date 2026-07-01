from typing import Any, TypedDict

from django.conf import settings
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph


ROLE_QUESTIONS = {
    "swe": [
        "Walk me through your resume and highlight the work most relevant to software engineering.",
        "Explain one project where you used data structures, APIs, or databases.",
        "What happens when a user enters a URL in the browser?",
        "How would you debug a slow Django or Python application?",
        "Why should we hire you as a software engineer?",
    ],
    "aiml": [
        "Walk me through your resume with focus on AI/ML exposure.",
        "Explain one ML or AI project from problem statement to result.",
        "What is overfitting, and how would you reduce it?",
        "How do you evaluate a classification model?",
        "Why are you interested in AI/ML roles?",
    ],
    "ds": [
        "Walk me through your resume with focus on data work.",
        "Explain a project where you cleaned, analyzed, or visualized data.",
        "How would you handle missing values in a dataset?",
        "What is the difference between correlation and causation?",
        "Why should we consider you for a data science role?",
    ],
    "app": [
        "Walk me through your resume with focus on app development.",
        "Explain one app you built and the main features you implemented.",
        "How do you manage app state and API calls?",
        "How would you improve app performance and user experience?",
        "Why do you want to work as an app developer?",
    ],
    "backend": [
        "Walk me through your resume with focus on backend development.",
        "Explain one backend project and its database design.",
        "What is the difference between authentication and authorization?",
        "How would you design a REST API for a mock interview platform?",
        "Why are you a good fit for backend development?",
    ],
    "frontend": [
        "Walk me through your resume with focus on frontend work.",
        "Explain one UI you built and how you made it user-friendly.",
        "What is the difference between client-side and server-side rendering?",
        "How would you make a page responsive and accessible?",
        "Why should we hire you for a frontend role?",
    ],
    "other": [
        "Walk me through your resume and target role.",
        "Explain one project that is closest to your selected role.",
        "What are the core skills needed for this role?",
        "Describe a challenge you faced and how you solved it.",
        "Why should we hire you for this role?",
    ],
}


class InterviewState(TypedDict, total=False):
    resume_text: str
    target_role: str
    custom_role: str
    resume_summary: dict[str, Any]
    interview_plan: list[dict[str, Any]]
    current_question: str
    answer_text: str
    evaluations: list[dict[str, Any]]
    user_remarks: str
    final_report: str


def get_llm():
    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=0.3,
    )


def analyze_resume(state: InterviewState) -> InterviewState:
    text = state.get("resume_text", "")
    state["resume_summary"] = {
        "summary": text[:700],
        "skills": [],
        "projects": [],
        "weak_areas": [],
    }
    return state


def create_interview_plan(state: InterviewState) -> InterviewState:
    role_key = state.get("target_role", "swe")
    questions = ROLE_QUESTIONS.get(role_key, ROLE_QUESTIONS["other"])
    state["interview_plan"] = [
        {"category": category, "question": question}
        for category, question in zip(
            ["resume", "project", "technical", "technical", "hr"],
            questions,
        )
    ]
    state["current_question"] = state["interview_plan"][0]["question"]
    return state


def evaluate_answer(state: InterviewState) -> InterviewState:
    answer = state.get("answer_text", "").strip()
    evaluations = state.get("evaluations", [])
    evaluations.append(
        {
            "score": 6 if answer else 0,
            "feedback": (
                "Starter evaluation: answer saved. Next step is connecting this node "
                "to the evaluator prompt and LLM."
            ),
            "missing_points": ["Add concrete examples", "Mention measurable impact"],
            "improved_answer": "",
        }
    )
    state["evaluations"] = evaluations
    return state


def create_final_report(state: InterviewState) -> InterviewState:
    state["final_report"] = (
        "Mock interview completed. Review your scores, improve weak areas, "
        "and run another interview for the same role."
    )
    return state


def build_interview_graph():
    graph = StateGraph(InterviewState)
    graph.add_node("analyze_resume", analyze_resume)
    graph.add_node("create_interview_plan", create_interview_plan)
    graph.add_node("evaluate_answer", evaluate_answer)
    graph.add_node("create_final_report", create_final_report)

    graph.set_entry_point("analyze_resume")
    graph.add_edge("analyze_resume", "create_interview_plan")
    graph.add_edge("create_interview_plan", "evaluate_answer")
    graph.add_edge("evaluate_answer", "create_final_report")
    graph.add_edge("create_final_report", END)
    return graph.compile()
