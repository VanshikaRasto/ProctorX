# services/exam_service.py
import json
import os
import uuid
import re
import glob
from datetime import datetime
from typing import List, Dict, Optional
from fastapi import HTTPException, status
from models.exam import Exam, ExamCreate, Question, ExamType, ExamStatus, ExamAssignment

class ExamService:
    def __init__(self):
        self.exams_dir = "data/exams"
        os.makedirs(self.exams_dir, exist_ok=True)

    def _load_exam_from_file(self, filepath: str) -> Optional[Exam]:
        """Load a single exam from file"""
        try:
            with open(filepath, 'r') as f:
                exam_data = json.load(f)
            
            # Convert created_at string back to datetime if needed
            if isinstance(exam_data.get('created_at'), str):
                exam_data['created_at'] = datetime.fromisoformat(exam_data['created_at'])
            
            # Ensure status is properly handled - convert string to enum if needed
            if isinstance(exam_data.get('status'), str):
                exam_data['status'] = ExamStatus(exam_data['status'])
            
            # Ensure exam_type is properly handled
            if isinstance(exam_data.get('exam_type'), str):
                exam_data['exam_type'] = ExamType(exam_data['exam_type'])
            
            return Exam(**exam_data)
        except Exception as e:
            print(f"Error loading exam from {filepath}: {e}")
            return None

    def _save_exam_to_file(self, exam: Exam):
        """Save exam to individual file"""
        filepath = os.path.join(self.exams_dir, f"{exam.id}.json")
        
        # Convert to dict and ensure proper serialization
        exam_dict = exam.dict()
        
        # Ensure datetime and enum values are properly serialized
        if isinstance(exam_dict.get('created_at'), datetime):
            exam_dict['created_at'] = exam_dict['created_at'].isoformat()
        
        # Ensure status is saved as string value
        if hasattr(exam_dict.get('status'), 'value'):
            exam_dict['status'] = exam_dict['status'].value
        elif isinstance(exam_dict.get('status'), ExamStatus):
            exam_dict['status'] = exam_dict['status'].value
        
        # Ensure exam_type is saved as string value
        if hasattr(exam_dict.get('exam_type'), 'value'):
            exam_dict['exam_type'] = exam_dict['exam_type'].value
        elif isinstance(exam_dict.get('exam_type'), ExamType):
            exam_dict['exam_type'] = exam_dict['exam_type'].value
        
        with open(filepath, 'w') as f:
            json.dump(exam_dict, f, indent=2, default=str)

    def _load_all_exams(self) -> List[Exam]:
        """Load all exams from individual files"""
        exams = []
        pattern = os.path.join(self.exams_dir, "*.json")
        
        for filepath in glob.glob(pattern):
            # Skip the old exams.json file if it exists
            if os.path.basename(filepath) == "exams.json":
                continue
                
            exam = self._load_exam_from_file(filepath)
            if exam:
                exams.append(exam)
        
        return exams

    def parse_txt_file(self, content: str, exam_type) -> List[Question]:
        """Parse .txt file content and extract questions - CORRECTED FOR YOUR FORMAT"""
        questions = []
        
        # Handle case where exam_type might be passed as string or enum
        if isinstance(exam_type, str):
            exam_type_value = exam_type
            exam_type_enum = ExamType(exam_type)
        else:
            exam_type_value = exam_type.value
            exam_type_enum = exam_type
        
        # Split content into question blocks
        # Each question starts with QUESTION_ID and ends before the next QUESTION_ID or end of file
        question_blocks = re.split(r'\n(?=QUESTION_ID:)', content.strip())
        
        for block in question_blocks:
            if not block.strip():
                continue
                
            lines = [line.strip() for line in block.strip().split('\n') if line.strip()]
            
            # Initialize question data
            question_data = {
                'id': None,
                'question': None,
                'type': exam_type_value,
                'options': [],
                'correct_answer': None,
                'points': 1
            }
            
            # Parse each line in the block
            parsing_options = False
            
            for line in lines:
                if line.startswith('QUESTION_ID:'):
                    question_data['id'] = line.split(':', 1)[1].strip()
                    
                elif line.startswith('TYPE:'):
                    question_data['type'] = line.split(':', 1)[1].strip()
                    
                elif line.startswith('POINTS:'):
                    try:
                        question_data['points'] = int(line.split(':', 1)[1].strip())
                    except ValueError:
                        question_data['points'] = 1
                        
                elif line.startswith('QUESTION:'):
                    question_data['question'] = line.split(':', 1)[1].strip()
                    
                elif line == 'OPTIONS:':
                    parsing_options = True
                    
                elif parsing_options and re.match(r'^[A-D]\)', line):
                    # Extract option text after "A) ", "B) ", etc.
                    option_text = line[3:].strip()  # Remove "A) " part
                    question_data['options'].append(option_text)
                    
                elif line.startswith('CORRECT:'):
                    correct_letter = line.split(':', 1)[1].strip()
                    # Convert letter to actual answer
                    if exam_type_enum == ExamType.MCQ and question_data['options']:
                        letter_to_index = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
                        if correct_letter in letter_to_index:
                            index = letter_to_index[correct_letter]
                            if index < len(question_data['options']):
                                question_data['correct_answer'] = question_data['options'][index]
            
            # Create Question object if we have required data
            if (question_data['id'] and 
                question_data['question'] and 
                (exam_type_enum != ExamType.MCQ or question_data['options'])):
                
                question = Question(
                    id=question_data['id'],
                    question=question_data['question'],
                    type=question_data['type'],
                    options=question_data['options'] if exam_type_enum == ExamType.MCQ else None,
                    correct_answer=question_data['correct_answer'],
                    points=question_data['points']
                )
                questions.append(question)
        
        if not questions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid questions found in the uploaded file. Please check the format."
            )
            
        return questions

    def create_exam(self, exam_data: ExamCreate, examiner_id: str) -> Exam:
        """Create a new exam from uploaded .txt file"""
        questions = self.parse_txt_file(exam_data.file_content, exam_data.exam_type)
        
        # Generate exam ID with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        exam_id = f"exam_{timestamp}"
        total_points = sum(q.points for q in questions)
        
        exam = Exam(
            id=exam_id,
            title=exam_data.title,
            description=exam_data.description,
            exam_type=exam_data.exam_type,
            branch=exam_data.branch,
            questions=questions,
            duration_minutes=exam_data.duration_minutes,
            total_points=total_points,
            created_by=examiner_id,
            created_at=datetime.now(),
            status=ExamStatus.DRAFT,
            assigned_students=[],
            approved_students=[]
        )
        
        # Save to individual file
        self._save_exam_to_file(exam)
        
        return exam

    def get_exam(self, exam_id: str) -> Optional[Exam]:
        """Get exam by ID"""
        filepath = os.path.join(self.exams_dir, f"{exam_id}.json")
        if os.path.exists(filepath):
            return self._load_exam_from_file(filepath)
        return None

    def get_exams_by_examiner(self, examiner_id: str) -> List[Exam]:
        """Get all exams created by an examiner"""
        all_exams = self._load_all_exams()
        return [exam for exam in all_exams if exam.created_by == examiner_id]

    def get_assigned_exams(self, student_id: str) -> List[Exam]:
        """Get exams assigned to a student that haven't been submitted yet"""
        from services.submission_service import submission_service  # Import here to avoid circular import
        
        all_exams = self._load_all_exams()
        assigned_exams = []
        
        for exam in all_exams:
            if student_id in exam.assigned_students:
                # Check if student has already submitted this exam
                existing_submission = submission_service.get_submission_by_student_exam(student_id, exam.id)
                if not existing_submission:
                    assigned_exams.append(exam)
        
        return assigned_exams

    def assign_exam(self, assignment: ExamAssignment, examiner_id: str):
        """Assign exam to students"""
        exam = self.get_exam(assignment.exam_id)
        
        if not exam:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exam not found"
            )
            
        # Check if examiner owns this exam
        if exam.created_by != examiner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only assign your own exams"
            )
        
        # Add students to assigned list
        current_assigned = set(exam.assigned_students)
        current_assigned.update(assignment.student_ids)
        exam.assigned_students = list(current_assigned)
        
        # Save updated exam
        self._save_exam_to_file(exam)
        
        return {"message": f"Exam assigned to {len(assignment.student_ids)} students"}

    def approve_student(self, exam_id: str, student_id: str, examiner_id: str):
        """Approve a student to take the exam"""
        exam = self.get_exam(exam_id)
        
        if not exam:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exam not found"
            )
            
        if exam.created_by != examiner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only approve students for your own exams"
            )
            
        if student_id not in exam.assigned_students:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Student is not assigned to this exam"
            )
        
        approved_students = set(exam.approved_students)
        approved_students.add(student_id)
        exam.approved_students = list(approved_students)
        
        # Save updated exam
        self._save_exam_to_file(exam)
        
        return {"message": "Student approved successfully"}

    def activate_exam(self, exam_id: str, examiner_id: str):
        """Activate an exam (make it available for taking)"""
        exam = self.get_exam(exam_id)
        
        if not exam:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exam not found"
            )
            
        if exam.created_by != examiner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only activate your own exams"
            )
        
        exam.status = ExamStatus.ACTIVE
        
        # Save updated exam
        self._save_exam_to_file(exam)
        
        return {"message": "Exam activated successfully"}

    def get_exam_for_student(self, exam_id: str, student_id: str) -> Exam:
        """Get exam questions for a student (without answers for MCQ)"""
        exam = self.get_exam(exam_id)
        
        if not exam:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exam not found"
            )
            
        if student_id not in exam.assigned_students:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not assigned to this exam"
            )
            
        if student_id not in exam.approved_students:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not approved to take this exam yet"
            )
            
        if exam.status != ExamStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This exam is not currently active"
            )
        
        # Remove correct answers from questions for students
        filtered_questions = []
        for question in exam.questions:
            q_dict = question.dict()
            if exam.exam_type == ExamType.MCQ:
                q_dict['correct_answer'] = None  # Hide correct answer
            filtered_questions.append(Question(**q_dict))
        
        exam.questions = filtered_questions
        return exam

    def get_all_active_exams(self) -> List[Exam]:
        """Get all active exams across all examiners - FIXED VERSION"""
        all_exams = self._load_all_exams()
        active_exams = []
        
        for exam in all_exams:
            # Handle different ways status might be stored/compared
            exam_status = exam.status
            
            # Convert to string for comparison if it's an enum
            if hasattr(exam_status, 'value'):
                status_str = exam_status.value
            else:
                status_str = str(exam_status)
            
            # Check if status is active
            if status_str.lower() == 'active':
                active_exams.append(exam)
        
        return active_exams

    def assign_and_approve_student(self, exam_id: str, student_id: str):
        """Add student to both assigned and approved lists"""
        exam = self.get_exam(exam_id)
        
        if not exam:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exam not found"
            )
        
        # Add to assigned students
        assigned_students = set(exam.assigned_students)
        assigned_students.add(student_id)
        exam.assigned_students = list(assigned_students)
        
        # Add to approved students
        approved_students = set(exam.approved_students)
        approved_students.add(student_id)
        exam.approved_students = list(approved_students)
        
        # Save updated exam
        self._save_exam_to_file(exam)
    def complete_exam(self, exam_id: str, examiner_id: str):
        """Mark exam as completed"""
        exam = self.get_exam(exam_id)
        
        if not exam:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exam not found"
            )
            
        if exam.created_by != examiner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only complete your own exams"
            )
        
        exam.status = ExamStatus.COMPLETED
        self._save_exam_to_file(exam)
        
        return {"message": "Exam marked as completed"}
# Global exam service instance
exam_service = ExamService()