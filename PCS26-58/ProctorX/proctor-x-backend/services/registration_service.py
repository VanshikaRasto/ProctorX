# services/registration_service.py
import json
import os
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import HTTPException, status
from models.exam import ExamRegistration, ExamRegistrationCreate, RegistrationStatus, ExamRegistrationUpdate
from services.exam_service import exam_service
from services.auth_service import auth_service

class RegistrationService:
    def __init__(self):
        self.registrations_file = "data/registrations/registrations.json"
        self._ensure_registrations_file()

    def _ensure_registrations_file(self):
        os.makedirs("data/registrations", exist_ok=True)
        if not os.path.exists(self.registrations_file):
            with open(self.registrations_file, 'w') as f:
                json.dump({}, f)

    def _load_registrations(self) -> dict:
        try:
            with open(self.registrations_file, 'r') as f:
                return json.load(f)
        except:
            return {}

    def _save_registrations(self, registrations: dict):
        with open(self.registrations_file, 'w') as f:
            json.dump(registrations, f, indent=2, default=str)

    def create_registration(self, registration_data: ExamRegistrationCreate, student_id: str) -> ExamRegistration:
        """Student requests to register for an exam"""
        registrations = self._load_registrations()
        
        # Check if exam exists and is active
        exam = exam_service.get_exam(registration_data.exam_id)
        if not exam:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exam not found"
            )
        
        if exam.status != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Exam is not available for registration"
            )
        
        # Check if student already registered
        for reg in registrations.values():
            if reg['exam_id'] == registration_data.exam_id and reg['student_id'] == student_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You have already registered for this exam"
                )
        
        # Get student info
        student = auth_service.get_user_by_id(student_id)
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found"
            )
        # Ensure student branch matches exam branch
        if getattr(student, 'branch', None) and getattr(exam, 'branch', None):
            if student.branch != exam.branch:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You cannot register for an exam outside your branch"
                )
        
        registration_id = str(uuid.uuid4())
        registration = ExamRegistration(
            id=registration_id,
            exam_id=registration_data.exam_id,
            student_id=student_id,
            student_name=student.full_name,
            student_email=student.email,
            status=RegistrationStatus.PENDING,
            requested_at=datetime.now(),
            notes=registration_data.notes
        )
        
        registrations[registration_id] = registration.dict()
        self._save_registrations(registrations)
        
        return registration

    def get_registrations_by_exam(self, exam_id: str) -> List[ExamRegistration]:
        """Get all registrations for an exam (for examiner)"""
        registrations = self._load_registrations()
        exam_registrations = []
        
        for reg_data in registrations.values():
            if reg_data['exam_id'] == exam_id:
                reg_data['requested_at'] = datetime.fromisoformat(reg_data['requested_at'])
                if reg_data.get('reviewed_at'):
                    reg_data['reviewed_at'] = datetime.fromisoformat(reg_data['reviewed_at'])
                exam_registrations.append(ExamRegistration(**reg_data))
        
        return exam_registrations

    def get_registrations_by_student(self, student_id: str) -> List[ExamRegistration]:
        """Get all registrations by a student"""
        registrations = self._load_registrations()
        student_registrations = []
        
        for reg_data in registrations.values():
            if reg_data['student_id'] == student_id:
                reg_data['requested_at'] = datetime.fromisoformat(reg_data['requested_at'])
                if reg_data.get('reviewed_at'):
                    reg_data['reviewed_at'] = datetime.fromisoformat(reg_data['reviewed_at'])
                student_registrations.append(ExamRegistration(**reg_data))
        
        return student_registrations

    def update_registration_status(self, registration_id: str, update_data: ExamRegistrationUpdate, examiner_id: str) -> ExamRegistration:
    
        registrations = self._load_registrations()
    
        if registration_id not in registrations:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Registration not found"
            )
        
        registration = registrations[registration_id]
        
        # Verify examiner owns the exam
        exam = exam_service.get_exam(registration['exam_id'])
        if not exam or exam.created_by != examiner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only review registrations for your own exams"
            )
        
        # Update registration - FIXED LINE
        registration['status'] = update_data.status  # Remove .value
        registration['reviewed_at'] = datetime.now().isoformat()
        registration['reviewed_by'] = examiner_id
        if update_data.notes:
            registration['notes'] = update_data.notes
        
        # If approved, add student to exam's assigned and approved lists
        if update_data.status == RegistrationStatus.APPROVED:
            exam_service.assign_and_approve_student(registration['exam_id'], registration['student_id'])
        
        registrations[registration_id] = registration
        self._save_registrations(registrations)
        
        # Convert back to model
        registration['requested_at'] = datetime.fromisoformat(registration['requested_at'])
        registration['reviewed_at'] = datetime.fromisoformat(registration['reviewed_at'])
        
        return ExamRegistration(**registration)

    def get_available_exams(self, student_id: str) -> List[dict]:
        """Get exams available for student registration"""
        # Get all active exams
        all_exams = exam_service.get_all_active_exams()
        # Filter exams by student's branch
        student = auth_service.get_user_by_id(student_id)
        if student and getattr(student, 'branch', None):
            student_branch = student.branch
            all_exams = [e for e in all_exams if getattr(e, 'branch', None) == student_branch]
        
        # Get student's existing registrations
        student_registrations = self.get_registrations_by_student(student_id)
        registered_exam_ids = {reg.exam_id for reg in student_registrations}
        
        # Get exams student is already assigned to
        assigned_exams = exam_service.get_assigned_exams(student_id)
        assigned_exam_ids = {exam.id for exam in assigned_exams}
        
        available_exams = []
        for exam in all_exams:
            if exam.id not in registered_exam_ids and exam.id not in assigned_exam_ids:
                # Get registration info if exists
                registration_status = None
                for reg in student_registrations:
                    if reg.exam_id == exam.id:
                        registration_status = reg.status
                        break
                
                exam_dict = exam.dict()
                exam_dict['registration_status'] = registration_status
                available_exams.append(exam_dict)
        
        return available_exams

    def debug_available_exams(self, student_id: str) -> dict:
        """Debug method to see why no exams are available"""
        print(f"=== DEBUG AVAILABLE EXAMS FOR STUDENT: {student_id} ===")
        
        # Get all active exams
        all_exams = exam_service.get_all_active_exams()
        print(f"Found {len(all_exams)} active exams")
        
        # Get student's existing registrations
        student_registrations = self.get_registrations_by_student(student_id)
        registered_exam_ids = {reg.exam_id for reg in student_registrations}
        print(f"Student has {len(student_registrations)} registrations: {registered_exam_ids}")
        
        # Get exams student is already assigned to
        assigned_exams = exam_service.get_assigned_exams(student_id)
        assigned_exam_ids = {exam.id for exam in assigned_exams}
        print(f"Student is assigned to {len(assigned_exams)} exams: {assigned_exam_ids}")
        
        debug_info = {
            "student_id": student_id,
            "total_active_exams": len(all_exams),
            "active_exams": [{"id": exam.id, "title": exam.title, "status": exam.status} for exam in all_exams],
            "registered_exam_ids": list(registered_exam_ids),
            "assigned_exam_ids": list(assigned_exam_ids),
            "student_registrations_count": len(student_registrations),
            "assigned_exams_count": len(assigned_exams)
        }
        
        print(f"Active exams details: {debug_info['active_exams']}")
        
        available_exams = []
        for exam in all_exams:
            is_registered = exam.id in registered_exam_ids
            is_assigned = exam.id in assigned_exam_ids
            is_available = not is_registered and not is_assigned
            
            print(f"Exam {exam.id} ({exam.title}): registered={is_registered}, assigned={is_assigned}, available={is_available}")
            
            exam_debug = {
                "exam_id": exam.id,
                "title": exam.title,
                "status": exam.status,
                "is_registered": is_registered,
                "is_assigned": is_assigned,
                "is_available": is_available
            }
            
            if is_available:
                available_exams.append(exam_debug)
        
        debug_info["available_exams"] = available_exams
        debug_info["final_available_count"] = len(available_exams)
        
        print(f"Final available exams: {len(available_exams)}")
        print("=== END DEBUG ===")
        
        return debug_info

# Global registration service instance
registration_service = RegistrationService()