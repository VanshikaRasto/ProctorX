# models/exam.py
# Import Pydantic components for data validation and serialization
from pydantic import BaseModel
# Import Enum for creating enumerated types
from enum import Enum
# Import typing utilities for complex type hints
from typing import List, Dict, Any, Optional
# Import datetime for timestamp handling
from datetime import datetime
# Import logging for debugging and monitoring
import logging
# Import regular expressions for text parsing
import re

# Set up logging for debugging exam parsing operations
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Exam type enumeration - defines the different types of exams supported
class ExamType(str, Enum):
    MCQ = "mcq"              # Multiple Choice Questions
    SUBJECTIVE = "subjective" # Essay/Written questions

# Exam status enumeration - represents the lifecycle state of an exam
class ExamStatus(str, Enum):
    DRAFT = "draft"           # Exam is being created, not yet active
    ACTIVE = "active"         # Exam is currently available for students
    COMPLETED = "completed"   # Exam has ended and submissions are closed
    ARCHIVED = "archived"     # Exam is stored for historical purposes

# Registration status enumeration - tracks the approval state of exam registrations
class RegistrationStatus(str, Enum):
    PENDING = "pending"       # Student has requested to take the exam
    APPROVED = "approved"     # Student is approved to take the exam
    REJECTED = "rejected"     # Student's request was denied

# Exam registration model - represents a student's request to take an exam
class ExamRegistration(BaseModel):
    id: str                              # Unique registration identifier
    exam_id: str                         # ID of the exam being registered for
    student_id: str                      # ID of the student registering
    student_email: str                   # Student's email address
    status: RegistrationStatus           # Current registration status
    requested_at: datetime               # When the registration was submitted
    reviewed_at: Optional[datetime] = None  # When the registration was reviewed
    reviewed_by: Optional[str] = None    # ID of the examiner who reviewed it
    notes: Optional[str] = None          # Additional notes about the registration

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# Model for creating new exam registrations
class ExamRegistrationCreate(BaseModel):
    exam_id: str              # ID of the exam to register for
    notes: Optional[str] = None  # Optional notes from the student

# Model for updating exam registration status (used by examiners)
class ExamRegistrationUpdate(BaseModel):
    status: RegistrationStatus  # New status to set
    notes: Optional[str] = None  # Optional notes about the decision

    class Config:
        use_enum_values = True
    
# Question model - represents a single question within an exam
class Question(BaseModel):
    id: str                              # Unique question identifier
    question: str                        # The question text
    type: str                            # Question type: "mcq" or "subjective"
    options: Optional[List[str]] = None  # List of answer options for MCQ questions
    correct_answer: Optional[str] = None # Correct answer for MCQ questions
    points: int = 1                      # Point value for this question

# Main Exam model - represents a complete exam with all questions and metadata
class Exam(BaseModel):
    id: str                              # Unique exam identifier
    title: str                           # Exam title/name
    description: str                     # Detailed description of the exam
    exam_type: ExamType                  # Type of exam (MCQ or subjective)
    questions: List[Question]            # List of questions in the exam
    duration_minutes: int                # Time limit in minutes
    total_points: int                    # Total points possible in the exam
    created_by: str                      # ID of the examiner who created the exam
    branch: str                          # Academic department/branch
    created_at: datetime                 # When the exam was created
    status: ExamStatus                   # Current exam status
    assigned_students: List[str] = []    # List of assigned student IDs
    approved_students: List[str] = []    # List of approved student IDs

    class Config:
        use_enum_values = True  # This ensures enums are serialized as their string values
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# Model for creating new exams (used by examiners)
class ExamCreate(BaseModel):
    title: str              # Exam title
    description: str         # Exam description
    exam_type: ExamType      # Type of exam
    duration_minutes: int    # Time limit in minutes
    file_content: str        # Raw .txt file content containing questions
    branch: str              # Academic department/branch

    class Config:
        use_enum_values = True

# Model for assigning exams to multiple students
class ExamAssignment(BaseModel):
    exam_id: str            # ID of the exam to assign
    student_ids: List[str]  # List of student IDs to assign the exam to

def parse_mcq_questions_debug(file_content: str) -> List[Question]:
    """
    Parse MCQ questions from text file content with extensive debugging.
    
    This function parses a structured text format containing multiple-choice questions.
    Expected format for each question:
    QUESTION_ID: q1
    TYPE: mcq
    POINTS: 2
    QUESTION: What is the capital of France?
    OPTIONS:
    A) London
    B) Berlin
    C) Paris
    D) Madrid
    CORRECT: C
    
    Args:
        file_content: Raw text content from the uploaded file
        
    Returns:
        List of Question objects parsed from the file
    """
    logger.debug(f"Received file content length: {len(file_content)}")
    logger.debug(f"First 200 chars of content: {repr(file_content[:200])}")
    
    questions = []
    
    if not file_content or not file_content.strip():
        logger.error("File content is empty or None")
        return questions
    
    # Normalize line endings first
    content = file_content.replace('\r\n', '\n').replace('\r', '\n')
    
    # Split content by double newlines to separate questions
    question_blocks = content.strip().split('\n\n')
    logger.debug(f"Found {len(question_blocks)} question blocks")
    
    for block_idx, block in enumerate(question_blocks):
        logger.debug(f"Processing block {block_idx + 1}: {repr(block[:100])}...")
        
        if not block.strip():
            logger.debug(f"Block {block_idx + 1} is empty, skipping")
            continue
            
        lines = [line.strip() for line in block.split('\n') if line.strip()]
        logger.debug(f"Block {block_idx + 1} has {len(lines)} lines")
        
        question_data = {
            'id': '',
            'question': '',
            'type': 'mcq',
            'options': [],
            'correct_answer': '',
            'points': 1
        }
        
        i = 0
        while i < len(lines):
            line = lines[i]
            logger.debug(f"Processing line {i}: {repr(line)}")
            
            if line.startswith('QUESTION_ID:'):
                question_data['id'] = line.split(':', 1)[1].strip()
                logger.debug(f"Found ID: {question_data['id']}")
            
            elif line.startswith('TYPE:'):
                question_data['type'] = line.split(':', 1)[1].strip()
                logger.debug(f"Found type: {question_data['type']}")
            
            elif line.startswith('POINTS:'):
                try:
                    question_data['points'] = int(line.split(':', 1)[1].strip())
                    logger.debug(f"Found points: {question_data['points']}")
                except ValueError as e:
                    logger.error(f"Invalid points value: {line}, error: {e}")
            
            elif line.startswith('QUESTION:'):
                question_data['question'] = line.split(':', 1)[1].strip()
                logger.debug(f"Found question: {question_data['question'][:50]}...")
            
            elif line.startswith('OPTIONS:'):
                logger.debug("Found OPTIONS line, parsing options...")
                # Parse options
                i += 1
                options = []
                option_map = {}
                
                while i < len(lines) and lines[i].strip() and any(lines[i].startswith(letter + ')') for letter in ['A', 'B', 'C', 'D', 'E']):
                    option_line = lines[i].strip()
                    logger.debug(f"Processing option line: {repr(option_line)}")
                    
                    if ')' in option_line:
                        option_letter = option_line[0]
                        option_text = option_line[3:].strip()  # Remove "A) "
                        options.append(option_text)
                        option_map[option_letter] = option_text
                        logger.debug(f"Added option {option_letter}: {option_text}")
                    
                    i += 1
                
                question_data['options'] = options
                logger.debug(f"Total options found: {len(options)}")
                i -= 1  # Adjust for the outer loop increment
            
            elif line.startswith('CORRECT:'):
                correct_letter = line.split(':', 1)[1].strip()
                logger.debug(f"Found correct letter: {correct_letter}")
                
                # Convert letter to actual answer text
                if correct_letter in ['A', 'B', 'C', 'D', 'E']:
                    correct_index = ord(correct_letter) - ord('A')
                    if correct_index < len(question_data['options']):
                        question_data['correct_answer'] = question_data['options'][correct_index]
                        logger.debug(f"Set correct answer: {question_data['correct_answer']}")
                    else:
                        logger.error(f"Correct letter {correct_letter} index {correct_index} out of range for options: {question_data['options']}")
                else:
                    logger.error(f"Invalid correct letter: {correct_letter}")
            
            i += 1
        
        # Validate required fields
        logger.debug(f"Question data for block {block_idx + 1}: {question_data}")
        
        required_fields = ['id', 'question', 'options', 'correct_answer']
        missing_fields = []
        
        for field in required_fields:
            if not question_data[field]:
                missing_fields.append(field)
        
        if missing_fields:
            logger.error(f"Block {block_idx + 1} missing required fields: {missing_fields}")
            logger.error(f"Question data: {question_data}")
        else:
            try:
                question = Question(**question_data)
                questions.append(question)
                logger.info(f"Successfully created question {question_data['id']}")
            except Exception as e:
                logger.error(f"Failed to create Question object: {e}")
                logger.error(f"Question data: {question_data}")
    
    logger.info(f"Total valid questions created: {len(questions)}")
    return questions

def parse_mcq_questions_simple(file_content: str) -> List[Question]:
    """
    Simpler, more forgiving parser for MCQ questions.
    
    This function provides a more relaxed parsing approach that can handle
    variations in formatting and missing optional fields.
    
    Args:
        file_content: Raw text content from the uploaded file
        
    Returns:
        List of Question objects parsed from the file
    """
    questions = []
    
    if not file_content:
        return questions
    
    # Normalize line endings
    content = file_content.replace('\r\n', '\n').replace('\r', '\n')
    
    # Split by empty lines (one or more)
    blocks = re.split(r'\n\s*\n', content.strip())
    
    for block in blocks:
        if not block.strip():
            continue
            
        lines = [line.strip() for line in block.split('\n') if line.strip()]
        
        # Initialize question data
        q_data = {}
        options = []
        
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().upper()
                value = value.strip()
                
                if key == 'QUESTION_ID':
                    q_data['id'] = value
                elif key == 'TYPE':
                    q_data['type'] = value.lower()
                elif key == 'POINTS':
                    try:
                        q_data['points'] = int(value)
                    except ValueError:
                        q_data['points'] = 1
                elif key == 'QUESTION':
                    q_data['question'] = value
                elif key == 'CORRECT':
                    correct_letter = value.upper()
                    if correct_letter in 'ABCDE':
                        q_data['correct_letter'] = correct_letter
            
            # Parse options (A), B), C), etc.)
            elif re.match(r'^[A-E]\)', line):
                option_text = line[3:].strip()  # Remove "A) "
                options.append(option_text)
        
        # Set correct answer based on letter
        if options and 'correct_letter' in q_data:
            correct_index = ord(q_data['correct_letter']) - ord('A')
            if 0 <= correct_index < len(options):
                q_data['correct_answer'] = options[correct_index]
        
        q_data['options'] = options
        
        # Validate and create question
        if all(k in q_data for k in ['id', 'question', 'type', 'options', 'correct_answer']) and q_data['options']:
            try:
                question = Question(**q_data)
                questions.append(question)
            except Exception as e:
                logger.error(f"Failed to create question: {e}, data: {q_data}")
    
    return questions

def create_exam_from_file(exam_data: ExamCreate, created_by: str) -> Exam:
    """
    Create an Exam object from ExamCreate data with parsed questions.
    
    This function takes exam creation data and parses the file content
    to extract questions, then creates a complete Exam object.
    
    Args:
        exam_data: ExamCreate object containing exam metadata and file content
        created_by: ID of the user creating the exam
        
    Returns:
        Complete Exam object with parsed questions
        
    Raises:
        ValueError: If no valid questions can be parsed from the file
    """
    logger.info(f"Creating exam: {exam_data.title}")
    logger.debug(f"File content preview: {exam_data.file_content[:200]}...")
    
    # Try the debug parser first
    questions = parse_mcq_questions_debug(exam_data.file_content)
    
    if not questions:
        logger.error("No valid questions found after debug parsing")
        
        # Try the simple parser as fallback
        logger.info("Trying simple parser as fallback...")
        questions = parse_mcq_questions_simple(exam_data.file_content)
    
    if not questions:
        raise ValueError("No valid questions found in the uploaded file. Please check the format.")
    
    total_points = sum(q.points for q in questions)
    
    exam = Exam(
        id=f"exam_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        title=exam_data.title,
        description=exam_data.description,
        exam_type=exam_data.exam_type,
        questions=questions,
        duration_minutes=exam_data.duration_minutes,
        total_points=total_points,
        created_by=created_by,
        created_at=datetime.now(),
        status=ExamStatus.DRAFT
    )
    
    logger.info(f"Successfully created exam with {len(questions)} questions, {total_points} total points")
    return exam