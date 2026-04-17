# routers/students.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List
from pydantic import ValidationError
import logging
from models.exam import Exam
from models.submission import Submission, SubmissionCreate
from models.user import User, UserRole
from services.exam_service import exam_service  # Import the instance
from services.submission_service import submission_service  # Import the instance
from services.auth_service import verify_token, get_current_user

logger = logging.getLogger(__name__)
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

@router.get("/my-exams", response_model=List[Exam])
async def get_assigned_exams(
    current_user: User = Depends(get_current_student)
):
    """Get all exams assigned to the current student"""
    return exam_service.get_assigned_exams(current_user.id)

@router.get("/exam/{exam_id}", response_model=Exam)
async def get_exam_for_taking(
    exam_id: str,
    current_user: User = Depends(get_current_student)
):
    """Get exam questions for taking (without answers)"""
    return exam_service.get_exam_for_student(exam_id, current_user.id)

@router.post("/test-submission-format")
async def test_submission_format(
    request_body: dict,
    current_user: User = Depends(get_current_student)
):
    """Test endpoint to debug submission format without processing"""
    logger.info(f"Testing submission format for student {current_user.id}")
    
    try:
        # Log the raw request body
        logger.debug(f"Raw request body: {request_body}")
        
        # Try to parse as SubmissionCreate
        try:
            submission_data = SubmissionCreate(**request_body)
            logger.info("Successfully parsed as SubmissionCreate")
            
            # Test each answer
            answer_results = []
            for i, answer in enumerate(submission_data.answers):
                answer_results.append({
                    "index": i,
                    "question_id": answer.question_id,
                    "question_id_type": str(type(answer.question_id)),
                    "answer_length": len(answer.answer) if answer.answer else 0
                })
            
            return {
                "status": "success", 
                "message": "Submission format is valid",
                "exam_id": submission_data.exam_id,
                "answers_count": len(submission_data.answers),
                "answers": answer_results[:5]  # First 5 for debugging
            }
            
        except ValidationError as ve:
            error_details = []
            for error in ve.errors():
                error_details.append({
                    "field": error.get('loc', []),
                    "message": error.get('msg', ''),
                    "type": error.get('type', ''),
                    "input": str(error.get('input', ''))[:100]  # Truncate long inputs
                })
            
            return {
                "status": "validation_error",
                "message": "Submission format validation failed", 
                "errors": error_details,
                "raw_body_keys": list(request_body.keys()) if isinstance(request_body, dict) else "not_dict"
            }
            
    except Exception as e:
        logger.error(f"Test submission format failed: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e),
            "raw_body_type": str(type(request_body))
        }

@router.post("/submit", response_model=Submission)
async def submit_exam(
    submission_data: SubmissionCreate,
    current_user: User = Depends(get_current_student)
):
    """Submit exam answers"""
    logger.info(f"Submission request from student {current_user.id} for exam {submission_data.exam_id}")
    
    try:
        # Debug: Log the raw request data
        logger.debug(f"Raw submission_data type: {type(submission_data)}")
        
        # Try to get dict representation safely
        try:
            data_dict = submission_data.dict()
            logger.debug(f"Submission data dict: {data_dict}")
            logger.debug(f"Number of answers: {len(submission_data.answers)}")
            
            # Log each answer specifically
            for i, answer in enumerate(submission_data.answers):
                logger.debug(f"Answer {i}: question_id='{answer.question_id}' (type: {type(answer.question_id)}), answer length: {len(answer.answer) if answer.answer else 0}")
                
        except Exception as debug_error:
            logger.error(f"Could not debug submission data: {debug_error}")
        
        # Create submission
        result = submission_service.create_submission(submission_data, current_user.id)
        logger.info(f"Submission created successfully: {result.id}")
        
        return result
        
    except ValidationError as ve:
        # Simple error formatting
        logger.error(f"Validation error: {ve}")
        error_msg = f"Validation failed: {str(ve)}"
        
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error_msg
        )
    except Exception as e:
        logger.error(f"Unexpected error in submit_exam: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit exam: {str(e)}"
        )

@router.get("/submissions", response_model=List[Submission])
async def get_my_submissions(
    current_user: User = Depends(get_current_student)
):
    """Get all submissions by the current student"""
    return submission_service.get_submissions_by_student(current_user.id)