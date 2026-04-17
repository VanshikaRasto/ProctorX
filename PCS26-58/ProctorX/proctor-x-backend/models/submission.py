# models/submission.py
from pydantic import BaseModel, validator
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from models.violation import ViolationCreate

class Answer(BaseModel):
    question_id: str  # Change back to string to match what frontend sends
    answer: str
    time_spent_seconds: Optional[int] = None
    question_type: Optional[str] = None  # mcq, text, etc.

class ProctoringData(BaseModel):
    violations_count: int = 0
    tab_switch_count: int = 0
    face_detection_violations: int = 0
    hand_detection_violations: int = 0
    object_detection_violations: int = 0
    proctoring_active: bool = False
    camera_enabled: bool = False
    microphone_enabled: bool = False

class Submission(BaseModel):
    id: str
    exam_id: str
    student_id: str
    student_name: str
    answers: List[Answer]
    submitted_at: datetime
    time_taken_minutes: int
    violations: List[str] = []  # Keep as string list for backward compatibility
    status: str = "submitted"  # submitted, graded, revoked
    
    # New fields
    exam_status: Optional[str] = "completed"  # completed, revoked
    total_questions: Optional[int] = None
    answered_questions: Optional[int] = None
    submission_timestamp: Optional[datetime] = None
    proctoring_data: Optional[ProctoringData] = None

class SubmissionCreate(BaseModel):
    exam_id: str
    student_id: Optional[Union[int, str]] = None  # Accept both types
    answers: List[Answer]
    time_taken_minutes: int
    violations: List[str] = []  # Keep simple for backward compatibility
    
    # New optional fields that frontend sends
    exam_status: Optional[str] = "completed"
    total_questions: Optional[int] = None
    answered_questions: Optional[int] = None
    submission_timestamp: Optional[str] = None  # Will be converted to datetime
    proctoring_data: Optional[ProctoringData] = None
    
    # For detailed violation objects (will be processed separately)
    detailed_violations: Optional[List[Dict[str, Any]]] = None
    
    @validator('student_id', pre=True)
    def convert_student_id(cls, v):
        """Convert student_id to string if it's an int"""
        if v is not None:
            return str(v)
        return v

class SubmissionWithViolations(BaseModel):
    """Extended submission model that includes full violation details"""
    submission: Submission
    violation_details: List[Dict[str, Any]] = []