def build_recommendations(evaluations):
    """Return simple study recommendations from evaluation results."""
    if not evaluations:
        return ["Practice explaining your resume and one strong project clearly."]

    return [
        "Revise weak technical topics from your interview feedback.",
        "Prepare one project story using problem, approach, result, and learning.",
        "Practice short and confident HR answers.",
    ]
