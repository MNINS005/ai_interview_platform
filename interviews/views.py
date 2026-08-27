import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

from feedback.models import Evaluation, FinalReport
from resumes.models import Resume
from resumes.services import extract_text_from_pdf

from .forms import AnswerForm, FinalRemarksForm, InterviewStartForm
from .langgraph_flow import (
    INTRO_QUESTION,
    TOPIC_SEQUENCE,
    build_interview_graph,
    create_final_report,
    evaluate_answer,
    generate_next_question,
)
from .models import Answer, InterviewSession, Question
from .voice_services import transcribe_audio_file


def home(request):
    return render(request, "interviews/home.html")


@login_required
def dashboard(request):
    sessions = InterviewSession.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "interviews/dashboard.html", {"sessions": sessions})


def build_resume_from_form(user, form):
    resume_file = form.cleaned_data.get("resume_file")
    pasted_text = form.cleaned_data.get("resume_text", "").strip()

    resume = Resume.objects.create(
        user=user,
        title=resume_file.name if resume_file else "Pasted Resume",
        file=resume_file,
        raw_text=pasted_text,
    )

    if resume.file:
        extracted_text = extract_text_from_pdf(resume.file.path)
        resume.raw_text = extracted_text or pasted_text
        resume.save(update_fields=["raw_text"])

    return resume


def _previous_session_questions(user, target_role, exclude_session_id=None):
    queryset = Question.objects.filter(session__user=user, session__target_role=target_role)
    if exclude_session_id:
        queryset = queryset.exclude(session_id=exclude_session_id)
    return list(queryset.order_by("-created_at").values_list("text", flat=True)[:15])


def _build_transcript(session):
    transcript = []
    for question_obj in session.questions.select_related("answer__evaluation").order_by("order"):
        answer = getattr(question_obj, "answer", None)
        if not answer:
            continue
        evaluation = getattr(answer, "evaluation", None)
        transcript.append(
            {
                "category": question_obj.category,
                "question": question_obj.text,
                "answer": answer.text,
                "feedback": evaluation.feedback if evaluation else "",
            }
        )
    return transcript


def _topic_progress(category):
    total_topics = len(TOPIC_SEQUENCE) + 1
    if category not in TOPIC_SEQUENCE:
        return 1, total_topics
    return TOPIC_SEQUENCE.index(category) + 2, total_topics


@login_required
def start_interview(request):
    if request.method == "POST":
        form = InterviewStartForm(request.POST, request.FILES)
        if form.is_valid():
            resume = build_resume_from_form(request.user, form)
            if not resume.raw_text.strip():
                messages.error(
                    request,
                    "I could not read text from that PDF. Please paste resume text instead.",
                )
                resume.delete()
                return render(request, "interviews/start.html", {"form": form})

            graph = build_interview_graph()
            result = graph.invoke({"resume_text": resume.raw_text})

            session = InterviewSession.objects.create(
                user=request.user,
                resume=resume,
                target_role=form.cleaned_data["target_role"],
                custom_role=form.cleaned_data["custom_role"],
                resume_summary=result.get("resume_summary", {}),
            )

            Question.objects.create(
                session=session,
                text=INTRO_QUESTION,
                category="intro",
                order=1,
            )

            return redirect("interviews:question", session_id=session.id)
    else:
        form = InterviewStartForm()

    return render(request, "interviews/start.html", {"form": form})


@login_required
def question(request, session_id):
    session = get_object_or_404(InterviewSession, id=session_id, user=request.user)
    current_question = session.questions.filter(answer__isnull=True).order_by("order").first()
    if current_question is None:
        return redirect("interviews:final_remarks", session_id=session.id)

    if request.method == "POST":
        form = AnswerForm(request.POST)
        if form.is_valid():
            answer, _ = Answer.objects.update_or_create(
                question=current_question,
                defaults={"text": form.cleaned_data["answer_text"]},
            )

            eval_state = evaluate_answer(
                {
                    "current_question": current_question.text,
                    "answer_text": form.cleaned_data["answer_text"],
                    "target_role": session.target_role,
                    "custom_role": session.custom_role,
                }
            )
            evaluation_data = eval_state["evaluations"][-1]
            Evaluation.objects.update_or_create(
                answer=answer,
                defaults={
                    "score": evaluation_data["score"],
                    "feedback": evaluation_data["feedback"],
                    "missing_points": evaluation_data["missing_points"],
                    "improved_answer": evaluation_data["improved_answer"],
                },
            )

            next_state = generate_next_question(
                {
                    "target_role": session.target_role,
                    "custom_role": session.custom_role,
                    "resume_summary": session.resume_summary,
                    "previous_questions": _previous_session_questions(
                        request.user, session.target_role, exclude_session_id=session.id
                    ),
                    "transcript": _build_transcript(session),
                    "topic_index": session.topic_index,
                    "followups_used": session.followups_used,
                }
            )

            if next_state.get("interview_complete"):
                return redirect("interviews:final_remarks", session_id=session.id)

            session.topic_index = next_state["topic_index"]
            session.followups_used = next_state["followups_used"]
            session.save(update_fields=["topic_index", "followups_used"])

            Question.objects.create(
                session=session,
                text=next_state["current_question"],
                category=next_state["current_category"],
                order=current_question.order + 1,
            )

            return redirect("interviews:question", session_id=session.id)
    else:
        existing_answer = getattr(current_question, "answer", None)
        initial = {"answer_text": existing_answer.text} if existing_answer else None
        form = AnswerForm(initial=initial)

    topic_number, total_topics = _topic_progress(current_question.category)

    return render(
        request,
        "interviews/question.html",
        {
            "form": form,
            "session": session,
            "question": current_question,
            "progress": current_question.order,
            "topic_number": topic_number,
            "total_topics": total_topics,
        },
    )


@login_required
@require_POST
def transcribe_audio(request):
    audio_file = request.FILES.get("audio")
    if not audio_file:
        return JsonResponse({"error": "No audio received."}, status=400)

    try:
        text = transcribe_audio_file(audio_file)
    except Exception:
        logger.exception("Audio transcription failed")
        return JsonResponse(
            {"error": "Could not transcribe audio. Please try again or type your answer."},
            status=400,
        )

    return JsonResponse({"text": text})


@login_required
def final_remarks(request, session_id):
    session = get_object_or_404(InterviewSession, id=session_id, user=request.user)

    if request.method == "POST":
        form = FinalRemarksForm(request.POST)
        if form.is_valid():
            session.user_remarks = form.cleaned_data["user_remarks"]
            session.status = "completed"
            session.save(update_fields=["user_remarks", "status"])

            evaluations = Evaluation.objects.filter(answer__question__session=session)
            report_state = create_final_report(
                {
                    "target_role": session.target_role,
                    "custom_role": session.custom_role,
                    "evaluations": [
                        {"score": evaluation.score, "feedback": evaluation.feedback}
                        for evaluation in evaluations
                    ],
                    "user_remarks": form.cleaned_data["user_remarks"],
                }
            )
            report_details = report_state["final_report_details"]
            FinalReport.objects.update_or_create(
                session=session,
                defaults={
                    "strengths": report_details["strengths"],
                    "weak_areas": report_details["weak_areas"],
                    "recommendations": report_details["recommendations"],
                    "summary": report_details["summary"],
                },
            )
            return redirect("interviews:report", session_id=session.id)
    else:
        form = FinalRemarksForm(initial={"user_remarks": session.user_remarks})

    return render(request, "interviews/final_remarks.html", {"form": form, "session": session})


@login_required
def report(request, session_id):
    session = get_object_or_404(InterviewSession, id=session_id, user=request.user)
    questions = session.questions.select_related("answer__evaluation")
    report_obj = getattr(session, "final_report", None)
    return render(
        request,
        "interviews/report.html",
        {"session": session, "questions": questions, "report": report_obj},
    )
