from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List
from models.exam import Exam, ExamCreate, ExamAssignment
from models.user import User, UserRole
from services.exam_service import exam_service
from services.auth_service import verify_token, get_current_user

router = APIRouter()
security = HTTPBearer()

def get_current_examiner(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    token_data = verify_token(credentials.credentials)
    user = get_current_user(token_data)
    if user.role != UserRole.EXAMINER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Examiner access required"
        )
    return user

@router.post("/", response_model=Exam)
async def create_exam(
    exam_data: ExamCreate,
    current_user: User = Depends(get_current_examiner)
):
    """Create a new exam from uploaded .txt file"""
    return exam_service.create_exam(exam_data, current_user.id)

@router.get("/my-exams", response_model=List[Exam])
async def get_my_exams(
    current_user: User = Depends(get_current_examiner)
):
    """Get all exams created by the current examiner"""
    return exam_service.get_exams_by_examiner(current_user.id)

@router.get("/{exam_id}", response_model=Exam)
async def get_exam(
    exam_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get exam details"""
    token_data = verify_token(credentials.credentials)
    user = get_current_user(token_data)
    
    exam = exam_service.get_exam(exam_id)
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam not found"
        )
    
    # Check permissions
    if user.role == UserRole.EXAMINER and exam.created_by != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own exams"
        )
    elif user.role == UserRole.STUDENT:
        # Students get filtered exam (without answers)
        return exam_service.get_exam_for_student(exam_id, user.id)
    
    return exam

@router.post("/{exam_id}/assign")
async def assign_exam(
    exam_id: str,
    assignment: ExamAssignment,
    current_user: User = Depends(get_current_examiner)
):
    """Assign exam to students"""
    assignment.exam_id = exam_id
    return exam_service.assign_exam(assignment, current_user.id)

@router.post("/{exam_id}/approve/{student_id}")
async def approve_student(
    exam_id: str,
    student_id: str,
    current_user: User = Depends(get_current_examiner)
):
    """Approve a student to take the exam"""
    return exam_service.approve_student(exam_id, student_id, current_user.id)

@router.post("/{exam_id}/activate")
async def activate_exam(
    exam_id: str,
    current_user: User = Depends(get_current_examiner)
):
    """Activate an exam"""
    return exam_service.activate_exam(exam_id, current_user.id)
@router.post("/{exam_id}/complete")
async def complete_exam(
    exam_id: str,
    current_user: User = Depends(get_current_examiner)
):
    """Mark exam as completed"""
    return exam_service.complete_exam(exam_id, current_user.id)

@router.get("/{exam_id}/submissions")
async def get_exam_submissions(
    exam_id: str,
    current_user: User = Depends(get_current_examiner)
):
    """Get all submissions for an exam"""
    from services.submission_service import submission_service
    return submission_service.get_submissions_by_exam(exam_id)