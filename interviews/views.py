from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from feedback.models import Evaluation, FinalReport
from recommender.services import build_recommendations
from resumes.models import Resume
from resumes.services import extract_text_from_pdf

from .forms import AnswerForm, FinalRemarksForm, InterviewStartForm
from .langgraph_flow import build_interview_graph
from .models import Answer, InterviewSession, Question


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
            result = graph.invoke(
                {
                    "resume_text": resume.raw_text,
                    "target_role": form.cleaned_data["target_role"],
                    "custom_role": form.cleaned_data["custom_role"],
                    "answer_text": "",
                }
            )

            session = InterviewSession.objects.create(
                user=request.user,
                resume=resume,
                target_role=form.cleaned_data["target_role"],
                custom_role=form.cleaned_data["custom_role"],
                plan={"questions": result.get("interview_plan", [])},
            )

            for index, item in enumerate(result.get("interview_plan", []), start=1):
                Question.objects.create(
                    session=session,
                    text=item["question"],
                    category=item["category"],
                    order=index,
                )

            return redirect("interviews:question", session_id=session.id, order=1)
    else:
        form = InterviewStartForm()

    return render(request, "interviews/start.html", {"form": form})


@login_required
def question(request, session_id, order):
    session = get_object_or_404(InterviewSession, id=session_id, user=request.user)
    current_question = get_object_or_404(Question, session=session, order=order)
    total_questions = session.questions.count()

    if request.method == "POST":
        form = AnswerForm(request.POST)
        if form.is_valid():
            answer, _ = Answer.objects.update_or_create(
                question=current_question,
                defaults={"text": form.cleaned_data["answer_text"]},
            )
            Evaluation.objects.update_or_create(
                answer=answer,
                defaults={
                    "score": 6,
                    "feedback": "Good start. Add more specific examples and explain your impact clearly.",
                    "missing_points": ["Specific example", "Result or learning"],
                    "improved_answer": "",
                },
            )

            next_order = order + 1
            if next_order <= total_questions:
                return redirect("interviews:question", session_id=session.id, order=next_order)
            return redirect("interviews:final_remarks", session_id=session.id)
    else:
        existing_answer = getattr(current_question, "answer", None)
        initial = {"answer_text": existing_answer.text} if existing_answer else None
        form = AnswerForm(initial=initial)

    return render(
        request,
        "interviews/question.html",
        {
            "form": form,
            "session": session,
            "question": current_question,
            "progress": order,
            "total_questions": total_questions,
        },
    )


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
            recommendations = build_recommendations(evaluations)
            FinalReport.objects.update_or_create(
                session=session,
                defaults={
                    "strengths": ["Completed all questions", "Practiced role-specific answers"],
                    "weak_areas": ["Add more detail and measurable impact"],
                    "recommendations": recommendations,
                    "summary": "Your interview is complete. Use the feedback to improve your next attempt.",
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
