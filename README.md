# AI Interview Prep

A student-friendly AI mock interview system built with Django and LangGraph.

## Features

- Django login/register flow
- Resume PDF upload or pasted resume text
- PDF text extraction with `pdfplumber`
- Role-based mock interview planning
- Browser speech-to-text answer input
- Question, answer, evaluation, and report storage
- PostgreSQL-ready deployment config

## Local Setup

```bash
cd C:\Users\ankus\OneDrive\Desktop\AI_INTERVIEW_PREP
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

## Environment Variables

Copy `.env.example` to `.env` locally and fill in your values.

For local PostgreSQL:

```text
DATABASE_ENGINE=postgresql
POSTGRES_DB=ai_interview_prep
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-postgres-password
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
```

For Render, use `DATABASE_URL` from the Render PostgreSQL service.

## Render Deployment

This project includes:

```text
build.sh
render.yaml
gunicorn
whitenoise
dj-database-url
```

On Render:

1. Push this repo to GitHub.
2. Create a new Blueprint from `render.yaml`, or create Web Service manually.
3. Add environment variables:
   - `DJANGO_ALLOWED_HOSTS=your-service.onrender.com`
   - `DJANGO_CSRF_TRUSTED_ORIGINS=https://your-service.onrender.com`
   - `OPENAI_API_KEY=your-key`
4. Deploy.

## Notes

For the first deployment, prefer pasted resume text. Local file uploads on hosted services are not ideal long-term; use Cloudinary, S3, or Supabase Storage later for production media.
