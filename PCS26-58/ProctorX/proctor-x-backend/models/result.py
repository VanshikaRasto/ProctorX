from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime

class QuestionResult(BaseModel):
    question_id: str
    student_answer: str
    correct_answer: Optional[str] = None
    points_awarded: int
    max_points: int
    is_correct: Optional[bool] = None

class Result(BaseModel):
    id: str
    exam_id: str
    student_id: str
    submission_id: str
    question_results: List[QuestionResult]
    total_score: int
    max_score: int
    percentage: float
    grade: Optional[str] = None
    evaluated_at: datetime
    evaluated_by: str
    released: bool = False
    released_at: Optional[datetime] = None
