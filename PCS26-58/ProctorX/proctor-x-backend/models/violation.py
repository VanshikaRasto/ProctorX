from pydantic import BaseModel
from enum import Enum
from datetime import datetime
from typing import Optional, Dict, Any

class ViolationType(str, Enum):
    TAB_SWITCH = "tab_switch"
    EYE_MOVEMENT = "eye_movement"
    PHONE_DETECTED = "phone_detected"
    FACE_NOT_VISIBLE = "face_not_visible"
    MULTIPLE_FACES = "multiple_faces"
    # Enhanced detection types (backward compatible)
    PALM_DETECTED = "palm_detected"
    HAND_GESTURES = "hand_gestures" 
    FACE_LOOKING_AWAY = "face_looking_away"
    SUSPICIOUS_OBJECT = "suspicious_object"
    MULTIPLE_PEOPLE = "multiple_people"
    EXAM_SUSPENDED = "exam_suspended"

class ViolationSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Violation(BaseModel):
    id: str
    exam_id: str
    student_name: str
    student_id: str
    type: ViolationType
    severity: ViolationSeverity
    description: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None
    action_taken: Optional[str] = None
    # Enhanced fields (optional for backward compatibility)
    confidence_score: Optional[float] = None
    detection_method: Optional[str] = None

class ViolationCreate(BaseModel):
    exam_id: str
    student_id: str
    type: ViolationType
    severity: ViolationSeverity
    description: str
    metadata: Optional[Dict[str, Any]] = None
    # Enhanced fields (optional)
    confidence_score: Optional[float] = None
    detection_method: Optional[str] = None