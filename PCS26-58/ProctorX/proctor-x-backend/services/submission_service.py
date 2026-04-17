# services/submission_service.py
import json
import os
import uuid
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import HTTPException, status
from pydantic import ValidationError
from models.submission import Submission, SubmissionCreate, Answer

# Set up logging
logger = logging.getLogger(__name__)

class SubmissionService:
    def __init__(self):
        self.submissions_dir = "data/submissions"
        os.makedirs(self.submissions_dir, exist_ok=True)

    def _get_submission_file_path(self, student_id: str, exam_id: str) -> str:
        """Get the file path for a student's exam submission"""
        return os.path.join(self.submissions_dir, f"{student_id}_{exam_id}.json")

    def _load_submission_file(self, filepath: str) -> Optional[dict]:
        """Load a single submission file"""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading submission file {filepath}: {e}")
        return None

    def _save_submission_file(self, filepath: str, submission_data: dict):
        """Save submission to individual file"""
        try:
            with open(filepath, 'w') as f:
                json.dump(submission_data, f, indent=2, default=str)
            logger.info(f"Submission saved to {filepath}")
        except Exception as e:
            logger.error(f"Error saving submission to {filepath}: {e}")
            raise

    def create_submission(self, submission_data: SubmissionCreate, student_id: str) -> Submission:
        """Create a new exam submission"""
        logger.info(f"Creating submission for student {student_id}")
        logger.debug(f"Submission data type: {type(submission_data)}")
        
        try:
            # Log the raw data for debugging
            if hasattr(submission_data, 'dict'):
                logger.debug(f"Submission data dict: {submission_data.dict()}")
            else:
                logger.debug(f"Submission data: {submission_data}")
            
            # Fetch student name
            student_name = ""
            try:
                from services.auth_service import auth_service
                user = auth_service.get_user_by_id(student_id)
                if user:
                    student_name = user.full_name
            except Exception as e:
                logger.debug(f"Could not fetch student name for {student_id}: {e}")
            
            # Check if student already submitted this exam
            filepath = self._get_submission_file_path(student_id, submission_data.exam_id)
            logger.debug(f"Checking for existing submission at: {filepath}")
            
            if os.path.exists(filepath):
                logger.warning(f"Student {student_id} already submitted exam {submission_data.exam_id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You have already submitted this exam"
                )
            
            # Validate answers - this will help catch the question_id conversion issues
            logger.debug(f"Processing {len(submission_data.answers)} answers")
            processed_answers = []
            
            for i, answer in enumerate(submission_data.answers):
                try:
                    logger.debug(f"Answer {i}: question_id={answer.question_id} (type: {type(answer.question_id)}), answer={answer.answer[:50]}...")
                    
                    # The Answer model's validator should handle the conversion
                    processed_answers.append(answer)
                    
                except Exception as e:
                    logger.error(f"Error processing answer {i}: {e}")
                    logger.error(f"Answer data: {answer}")
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Invalid answer format for question {i+1}: {str(e)}"
                    )
            
            logger.debug(f"Successfully processed {len(processed_answers)} answers")
            
            submission_id = str(uuid.uuid4())
            logger.debug(f"Generated submission ID: {submission_id}")
            
            # Create submission with processed answers and student name
            submission = Submission(
                id=submission_id,
                exam_id=submission_data.exam_id,
                student_id=student_id,  # This comes from the authenticated user
                student_name=student_name,  # Add student name
                answers=processed_answers,
                submitted_at=datetime.now(),
                time_taken_minutes=submission_data.time_taken_minutes,
                violations=submission_data.violations or []
            )
            
            logger.debug(f"Created submission object successfully")
            
            # Save to individual file
            submission_dict = submission.dict()
            logger.debug(f"Converting submission to dict for saving...")
            
            self._save_submission_file(filepath, submission_dict)
            
            logger.info(f"Successfully created submission {submission_id} for student {student_id}")
            return submission
            
        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except ValidationError as ve:
            # Handle pydantic validation errors
            logger.error(f"Validation error: {ve}")
            error_details = []
            for error in ve.errors():
                field = " -> ".join(str(loc) for loc in error['loc'])
                error_details.append(f"{field}: {error['msg']}")
            
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Validation failed: {'; '.join(error_details)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error creating submission: {e}", exc_info=True)
            logger.error(f"Submission data type: {type(submission_data)}")
            logger.error(f"Student ID type: {type(student_id)}")
            
            # Provide more specific error information
            if "question_id" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Invalid question ID format. Please ensure all question IDs are valid numbers."
                )
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create submission: {str(e)}"
            )

    def get_submission_by_student_exam(self, student_id: str, exam_id: str) -> Optional[Submission]:
        """Get submission by student and exam"""
        filepath = self._get_submission_file_path(student_id, exam_id)
        submission_data = self._load_submission_file(filepath)
        
        if submission_data:
            try:
                # Handle datetime parsing
                if isinstance(submission_data['submitted_at'], str):
                    submission_data['submitted_at'] = datetime.fromisoformat(submission_data['submitted_at'])
                return Submission(**submission_data)
            except Exception as e:
                logger.error(f"Error parsing submission data: {e}")
        return None

    def get_submissions_by_student(self, student_id: str) -> List[Submission]:
        """Get all submissions by a student"""
        logger.debug(f"Getting submissions for student: {student_id}")
        submissions = []
        
        try:
            for filename in os.listdir(self.submissions_dir):
                if filename.startswith(f"{student_id}_") and filename.endswith('.json'):
                    filepath = os.path.join(self.submissions_dir, filename)
                    submission_data = self._load_submission_file(filepath)
                    if submission_data:
                        if isinstance(submission_data['submitted_at'], str):
                            submission_data['submitted_at'] = datetime.fromisoformat(submission_data['submitted_at'])
                        submissions.append(Submission(**submission_data))
        except Exception as e:
            logger.error(f"Error getting submissions for student {student_id}: {e}")
        
        logger.debug(f"Found {len(submissions)} submissions for student {student_id}")
        return submissions

    def get_submissions_by_exam(self, exam_id: str) -> List[Submission]:
        """Get all submissions for an exam"""
        logger.debug(f"Getting submissions for exam: {exam_id}")
        submissions = []
        
        try:
            for filename in os.listdir(self.submissions_dir):
                if filename.endswith(f"_{exam_id}.json"):
                    filepath = os.path.join(self.submissions_dir, filename)
                    submission_data = self._load_submission_file(filepath)
                    if submission_data:
                        if isinstance(submission_data['submitted_at'], str):
                            submission_data['submitted_at'] = datetime.fromisoformat(submission_data['submitted_at'])
                        submissions.append(Submission(**submission_data))
        except Exception as e:
            logger.error(f"Error getting submissions for exam {exam_id}: {e}")
        
        logger.debug(f"Found {len(submissions)} submissions for exam {exam_id}")
        return submissions

# Global submission service instance
submission_service = SubmissionService()