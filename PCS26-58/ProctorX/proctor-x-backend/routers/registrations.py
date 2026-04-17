# routers/registrations.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List
from models.exam import ExamRegistration, ExamRegistrationCreate, ExamRegistrationUpdate
from models.user import User, UserRole
from services.registration_service import registration_service
from services.auth_service import verify_token, get_current_user

router = APIRouter()
security = HTTPBearer()

def get_current_student(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    token_data = verify_token(credentials.credentials)
    user = get_current_user(token_data)
    if user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student access required"
        )
    return user

def get_current_examiner(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    token_data = verify_token(credentials.credentials)
    user = get_current_user(token_data)
    if user.role != UserRole.EXAMINER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Examiner access required"
        )
    return user

@router.get("/available-exams")
async def get_available_exams(
    current_user: User = Depends(get_current_student)
):
    """Get exams available for student registration"""
    return registration_service.get_available_exams(current_user.id)

@router.get("/debug-available-exams")
async def debug_available_exams(
    current_user: User = Depends(get_current_student)
):
    """Debug why no exams are available"""
    return registration_service.debug_available_exams(current_user.id)

@router.post("/register", response_model=ExamRegistration)
async def register_for_exam(
    registration_data: ExamRegistrationCreate,
    current_user: User = Depends(get_current_student)
):
    """Student registers for an exam"""
    return registration_service.create_registration(registration_data, current_user.id)

@router.get("/my-registrations", response_model=List[ExamRegistration])
async def get_my_registrations(
    current_user: User = Depends(get_current_student)
):
    """Get student's exam registrations"""
    return registration_service.get_registrations_by_student(current_user.id)

@router.get("/exam/{exam_id}/registrations", response_model=List[ExamRegistration])
async def get_exam_registrations(
    exam_id: str,
    current_user: User = Depends(get_current_examiner)
):
    """Get all registrations for an exam (examiner only)"""
    return registration_service.get_registrations_by_exam(exam_id)

@router.put("/registrations/{registration_id}", response_model=ExamRegistration)
async def update_registration_status(
    registration_id: str,
    update_data: ExamRegistrationUpdate,
    current_user: User = Depends(get_current_examiner)
):
    """Approve/reject a registration (examiner only)"""
    return registration_service.update_registration_status(registration_id, update_data, current_user.id)