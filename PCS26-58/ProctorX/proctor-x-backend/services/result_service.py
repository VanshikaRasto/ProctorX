import json
import os
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import HTTPException, status
from models.result import Result, QuestionResult
from models.exam import ExamType
from services.exam_service import exam_service
from services.submission_service import submission_service

class ResultService:
    def __init__(self):
        self.results_file = "data/results/results.json"
        self._ensure_results_file()

    def _ensure_results_file(self):
        os.makedirs("data/results", exist_ok=True)
        if not os.path.exists(self.results_file):
            with open(self.results_file, 'w') as f:
                json.dump({}, f)

    def _load_results(self) -> dict:
        try:
            with open(self.results_file, 'r') as f:
                return json.load(f)
        except:
            return {}

    def _save_results(self, results: dict):
        with open(self.results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)

    def evaluate_mcq_submission(self, exam, submission) -> Result:
        """Automatically evaluate MCQ submission"""
        question_results = []
        total_score = 0
        
        correct_answers = {q.id: q.correct_answer for q in exam.questions}
        
        for answer in submission.answers:
            question = next((q for q in exam.questions if q.id == answer.question_id), None)
            if not question:
                continue
                
            correct_answer = correct_answers.get(answer.question_id)
            is_correct = answer.answer.strip().upper() == correct_answer.strip().upper() if correct_answer else False
            points_awarded = question.points if is_correct else 0
            total_score += points_awarded
            
            question_results.append(QuestionResult(
                question_id=answer.question_id,
                student_answer=answer.answer,
                correct_answer=correct_answer,
                points_awarded=points_awarded,
                max_points=question.points,
                is_correct=is_correct
            ))
        
        result_id = str(uuid.uuid4())
        percentage = (total_score / exam.total_points) * 100 if exam.total_points > 0 else 0
        
        result = Result(
            id=result_id,
            exam_id=exam.id,
            student_id=submission.student_id,
            submission_id=submission.id,
            question_results=question_results,
            total_score=total_score,
            max_score=exam.total_points,
            percentage=percentage,
            evaluated_at=datetime.now(),
            evaluated_by="system"
        )
        
        return result

    def create_subjective_result(self, exam, submission, evaluator_id: str) -> Result:
        """Create result template for subjective exam (manual evaluation)"""
        question_results = []
        
        for answer in submission.answers:
            question = next((q for q in exam.questions if q.id == answer.question_id), None)
            if not question:
                continue
                
            question_results.append(QuestionResult(
                question_id=answer.question_id,
                student_answer=answer.answer,
                points_awarded=0,
                max_points=question.points,
                is_correct=None
            ))
        
        result_id = str(uuid.uuid4())
        result = Result(
            id=result_id,
            exam_id=exam.id,
            student_id=submission.student_id,
            submission_id=submission.id,
            question_results=question_results,
            total_score=0,
            max_score=exam.total_points,
            percentage=0,
            evaluated_at=datetime.now(),
            evaluated_by=evaluator_id
        )
        
        return result

    def evaluate_exam_submissions(self, exam_id: str, evaluator_id: str):
        """Evaluate all submissions for an exam"""
        exam = exam_service.get_exam(exam_id)
        if not exam:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exam not found"
            )
        
        if exam.created_by != evaluator_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only evaluate your own exams"
            )
        
        submissions = submission_service.get_submissions_by_exam(exam_id)
        results = self._load_results()
        evaluated_count = 0
        
        for submission in submissions:
            existing_result = None
            for result_data in results.values():
                if result_data['submission_id'] == submission.id:
                    existing_result = result_data
                    break
            
            if existing_result:
                continue
            
            if exam.exam_type == ExamType.MCQ:
                result = self.evaluate_mcq_submission(exam, submission)
            else:
                result = self.create_subjective_result(exam, submission, evaluator_id)
            
            results[result.id] = result.dict()
            evaluated_count += 1
        
        self._save_results(results)
        
        return {
            "message": f"Evaluated {evaluated_count} submissions",
            "exam_type": exam.exam_type,
            "auto_evaluated": exam.exam_type == ExamType.MCQ
        }

    def release_result(self, result_id: str, evaluator_id: str):
        """Release a result to student"""
        results = self._load_results()
        
        if result_id not in results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Result not found"
            )
        
        result_data = results[result_id]
        
        if result_data['evaluated_by'] != evaluator_id and result_data['evaluated_by'] != "system":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only release results you evaluated"
            )
        
        result_data['released'] = True
        result_data['released_at'] = datetime.now().isoformat()
        
        results[result_id] = result_data
        self._save_results(results)
        
        return {"message": "Result released to student"}

    def get_results_by_student(self, student_id: str, released_only: bool = True) -> List[Result]:
        """Get results for a student"""
        results = self._load_results()
        student_results = []
        
        for result_data in results.values():
            if result_data['student_id'] == student_id:
                if released_only and not result_data.get('released', False):
                    continue
                
                result_data['evaluated_at'] = datetime.fromisoformat(result_data['evaluated_at'])
                if result_data.get('released_at'):
                    result_data['released_at'] = datetime.fromisoformat(result_data['released_at'])
                
                student_results.append(Result(**result_data))
        
        return student_results

    def get_results_by_exam(self, exam_id: str, evaluator_id: str) -> List[Result]:
        """Get all results for an exam"""
        exam = exam_service.get_exam(exam_id)
        if not exam:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exam not found"
            )
        
        if exam.created_by != evaluator_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view results for your own exams"
            )
        
        results = self._load_results()
        exam_results = []
        
        for result_data in results.values():
            if result_data['exam_id'] == exam_id:
                try:
                    result_data['evaluated_at'] = datetime.fromisoformat(result_data['evaluated_at'])
                    if result_data.get('released_at'):
                        result_data['released_at'] = datetime.fromisoformat(result_data['released_at'])
                    
                    exam_results.append(Result(**result_data))
                except Exception as e:
                    print(f"Error loading result: {e}")
                    continue
        
        return exam_results

    def disapprove_exam_submissions(self, exam_id: str, evaluator_id: str):
        """Disapprove all submissions for an exam and give 0 marks"""
        exam = exam_service.get_exam(exam_id)
        if not exam:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exam not found"
            )
        
        if exam.created_by != evaluator_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only disapprove results for your own exams"
            )
        
        # Get all submissions for this exam
        submissions = submission_service.get_submissions_by_exam(exam_id)
        results = self._load_results()
        
        disapproved_count = 0
        
        for submission in submissions:
            # Create a result with 0 marks
            result_id = str(uuid.uuid4())
            
            # Calculate total possible points
            total_points = sum(q.points for q in exam.questions)
            
            result = Result(
                id=result_id,
                exam_id=exam_id,
                student_id=submission.student_id,
                student_name=submission.student_name,
                total_score=0,  # Give 0 marks
                max_score=total_points,
                percentage=0.0,  # 0%
                question_results=[],  # No detailed question results needed
                evaluated_at=datetime.now(),
                released=False,
                evaluator_id=evaluator_id,
                evaluation_notes="Exam disapproved - all students given 0 marks"
            )
            
            # Save result
            results[result_id] = result.dict()
            disapproved_count += 1
        
        # Save all results
        self._save_results(results)
        
        return {
            "message": f"Exam disapproved successfully",
            "disapproved_submissions": disapproved_count,
            "total_points": sum(q.points for q in exam.questions)
        }

# Global service instance
result_service = ResultService()