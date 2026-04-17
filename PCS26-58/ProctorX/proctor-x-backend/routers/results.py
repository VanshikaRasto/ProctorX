# routers/results.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List
from models.result import Result
from models.user import User, UserRole
from services.result_service import result_service  # Import the instance
from services.auth_service import verify_token, get_current_user

router = APIRouter()
security = HTTPBearer()

@router.get("/my-results", response_model=List[Result])
async def get_my_results(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get results for the current user"""
    token_data = verify_token(credentials.credentials)
    user = get_current_user(token_data)
    
    if user.role == UserRole.STUDENT:
        return result_service.get_results_by_student(user.id, released_only=True)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can view their results"
        )

@router.get("/exam/{exam_id}", response_model=List[Result])
async def get_exam_results(
    exam_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get all results for an exam (examiner only)"""
    token_data = verify_token(credentials.credentials)
    user = get_current_user(token_data)
    
    if user.role != UserRole.EXAMINER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Examiner access required"
        )
    
    return result_service.get_results_by_exam(exam_id, user.id)

@router.post("/{result_id}/release")
async def release_result(
    result_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Release a result to student"""
    token_data = verify_token(credentials.credentials)
    user = get_current_user(token_data)
    
    if user.role != UserRole.EXAMINER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Examiner access required"
        )
    
    return result_service.release_result(result_id, user.id)

@router.post("/exam/{exam_id}/evaluate")
async def evaluate_exam(
    exam_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Evaluate all submissions for an exam"""
    token_data = verify_token(credentials.credentials)
    user = get_current_user(token_data)
    
    if user.role != UserRole.EXAMINER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Examiner access required"
        )
    
    return result_service.evaluate_exam_submissions(exam_id, user.id)

@router.post("/exam/{exam_id}/disapprove")
async def disapprove_exam(
    exam_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Disapprove exam and give 0 marks to all students"""
    token_data = verify_token(credentials.credentials)
    user = get_current_user(token_data)
    
    if user.role != UserRole.EXAMINER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Examiner access required"
        )
    
    return result_service.disapprove_exam_submissions(exam_id, user.id)