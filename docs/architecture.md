# Architecture

## Simple MVP Flow

```text
User -> Django view -> Resume model -> LangGraph workflow -> Questions/Evaluations -> Final report
```

## LangGraph Nodes

1. `analyze_resume`
2. `create_interview_plan`
3. `evaluate_answer`
4. `create_final_report`

Keep this small until the MVP works. Add memory, scheduling, voice, or analytics only after the main interview flow is complete.
