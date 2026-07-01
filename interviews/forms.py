from django import forms

from .models import InterviewSession


class InterviewStartForm(forms.Form):
    target_role = forms.ChoiceField(
        choices=InterviewSession.ROLE_CHOICES,
        label="Target role",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    custom_role = forms.CharField(
        required=False,
        label="If other, mention role",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Example: DevOps Engineer",
            }
        ),
    )
    resume_file = forms.FileField(
        required=False,
        label="Upload resume PDF",
        widget=forms.ClearableFileInput(attrs={"class": "form-control", "accept": ".pdf"}),
    )
    resume_text = forms.CharField(
        required=False,
        label="Or paste resume text",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 10,
                "placeholder": "Paste your resume summary, skills, projects, and education here if you do not upload a PDF.",
            }
        ),
    )

    def clean_resume_file(self):
        resume_file = self.cleaned_data.get("resume_file")
        if not resume_file:
            return resume_file

        if not resume_file.name.lower().endswith(".pdf"):
            raise forms.ValidationError("Please upload a PDF resume.")

        max_size_mb = 5
        if resume_file.size > max_size_mb * 1024 * 1024:
            raise forms.ValidationError(f"Resume PDF must be under {max_size_mb} MB.")

        return resume_file

    def clean(self):
        cleaned_data = super().clean()
        target_role = cleaned_data.get("target_role")
        custom_role = cleaned_data.get("custom_role", "").strip()
        resume_file = cleaned_data.get("resume_file")
        resume_text = cleaned_data.get("resume_text", "").strip()

        if target_role == "other" and not custom_role:
            self.add_error("custom_role", "Please mention the role when selecting Other.")

        if not resume_file and not resume_text:
            raise forms.ValidationError("Upload a PDF resume or paste resume text.")

        return cleaned_data


class AnswerForm(forms.Form):
    answer_text = forms.CharField(
        label="Your answer",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 8,
                "placeholder": "Type here, or click Start live text and speak your answer.",
            }
        ),
    )


class FinalRemarksForm(forms.Form):
    user_remarks = forms.CharField(
        required=False,
        label="Final remarks",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 5,
                "placeholder": "Add anything you want the mentor report to remember.",
            }
        ),
    )
