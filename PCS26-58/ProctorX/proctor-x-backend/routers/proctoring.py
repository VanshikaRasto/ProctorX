from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import HTMLResponse
from typing import List, Optional
from models.violation import Violation, ViolationCreate, ViolationType
from models.user import User, UserRole
from services.proctoring_service import proctoring_service  # Enhanced service instance
from services.auth_service import verify_token, get_current_user
import logging

router = APIRouter()
security = HTTPBearer()
logger = logging.getLogger(__name__)

@router.post("/violations", response_model=Violation)
async def report_violation(
    violation_data: ViolationCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Report a proctoring violation (manual reporting)"""
    token_data = verify_token(credentials.credentials)
    user = get_current_user(token_data)
    
    # Only students can report their own violations
    if user.role == UserRole.STUDENT:
        violation_data.student_id = user.id
    
    return proctoring_service.create_violation(violation_data)

@router.get("/violations/exam/{exam_id}", response_model=List[Violation])
async def get_exam_violations(
    exam_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get all violations for an exam (examiner only)"""
    token_data = verify_token(credentials.credentials)
    user = get_current_user(token_data)
    
    if user.role != UserRole.EXAMINER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Examiner access required"
        )
    
    return proctoring_service.get_violations_by_exam(exam_id)

@router.get("/violations/student/{student_id}", response_model=List[Violation])
async def get_student_violations(
    student_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get violations for a student"""
    token_data = verify_token(credentials.credentials)
    user = get_current_user(token_data)
    
    # Students can only see their own violations
    if user.role == UserRole.STUDENT and user.id != student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own violations"
        )
    
    return proctoring_service.get_violations_by_student(student_id)

@router.post("/analyze-frame")
async def analyze_webcam_frame(
    exam_id: str,
    image: UploadFile = File(...),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Analyze webcam frame for violations using enhanced AI detection"""
    token_data = verify_token(credentials.credentials)
    user = get_current_user(token_data)
    
    if user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can submit monitoring frames"
        )
    
    # Validate file type
    if not image.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    # Read image data
    try:
        image_data = await image.read()
        logger.info(f"Processing frame for student {user.id} in exam {exam_id}")
        
        result = proctoring_service.analyze_frame(exam_id, user.id, image_data)
        
        # Log violations for monitoring
        if result.get('violations_detected', 0) > 0:
            logger.warning(f"Violations detected for student {user.id}: {result['violations_detected']}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing frame: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing image"
        )

@router.get("/violations/count/{exam_id}/{student_id}")
async def get_violation_count(
    exam_id: str,
    student_id: str,
    violation_type: Optional[ViolationType] = Query(None),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get violation count for a student in an exam"""
    token_data = verify_token(credentials.credentials)
    user = get_current_user(token_data)
    
    # Students can only see their own counts
    if user.role == UserRole.STUDENT and user.id != student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own violation counts"
        )
    
    if violation_type:
        count = proctoring_service.get_violation_count(exam_id, student_id, violation_type)
        return {"violation_type": violation_type.value, "count": count}
    else:
        # Get all violation counts by type
        all_violations = proctoring_service.get_violations_by_student(student_id)
        exam_violations = [v for v in all_violations if v.exam_id == exam_id]
        
        counts = {}
        for violation in exam_violations:
            violation_type = violation.type.value
            counts[violation_type] = counts.get(violation_type, 0) + 1
        
        return {"total_violations": len(exam_violations), "by_type": counts}

@router.get("/phone-tracking/{exam_id}/{student_id}")
async def get_phone_tracking_stats(
    exam_id: str,
    student_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get phone tracking statistics for a student in an exam"""
    token_data = verify_token(credentials.credentials)
    user = get_current_user(token_data)
    
    # Students can only see their own phone tracking stats
    if user.role == UserRole.STUDENT and user.id != student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own phone tracking statistics"
        )
    
    return proctoring_service.get_phone_tracking_stats(exam_id, student_id)

@router.post("/test-phone-tracking/{exam_id}/{student_id}")
async def test_phone_tracking(
    exam_id: str,
    student_id: str,
    confidence: float = 0.9,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Test phone tracking by simulating phone detections (debug endpoint)"""
    token_data = verify_token(credentials.credentials)
    user = get_current_user(token_data)
    
    if user.role != UserRole.EXAMINER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Examiner access required"
        )
    
    # Simulate phone detection
    result = proctoring_service._track_phone_detection(exam_id, student_id, confidence)
    
    return {
        "message": "Phone tracking test completed",
        "exam_id": exam_id,
        "student_id": student_id,
        "simulated_confidence": confidence,
        "tracking_result": result
    }

@router.get("/stats/{exam_id}")
async def get_exam_proctoring_stats(
    exam_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get comprehensive proctoring statistics for an exam"""
    token_data = verify_token(credentials.credentials)
    user = get_current_user(token_data)
    
    if user.role != UserRole.EXAMINER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Examiner access required"
        )
    
    return proctoring_service.get_detection_stats(exam_id)

@router.get("/health")
async def proctoring_health_check():
    """Check proctoring service health and AI model status"""
    try:
        # Test basic functionality
        test_result = {
            "status": "healthy",
            "ai_models": {
                "mediapipe_face": proctoring_service.face_detection is not None,
                "mediapipe_hands": proctoring_service.hands is not None,
                "mediapipe_face_mesh": proctoring_service.face_mesh is not None,
                "yolo_object_detection": proctoring_service.yolo_model is not None,
                "opencv_fallback": proctoring_service.face_cascade is not None
            },
            "detection_capabilities": [
                "face_detection",
                "hand_palm_detection", 
                "gaze_direction",
                "object_detection",
                "real_time_websocket"
            ]
        }
        
        # Count active models
        active_models = sum(1 for status in test_result["ai_models"].values() if status)
        test_result["active_models_count"] = active_models
        test_result["detection_confidence"] = "high" if active_models >= 4 else "medium" if active_models >= 2 else "low"
        
        return test_result
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Proctoring service unhealthy"
        )

@router.get("/frontend-monitoring-script", response_class=HTMLResponse)
async def get_frontend_monitoring_script():
    """Get JavaScript code for frontend real-time monitoring"""
    from routers.websocket_proctoring import FRONTEND_MONITORING_SCRIPT
    
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Proctoring Monitor Script</title>
        <style>
            .proctoring-alert {{
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 10000;
                max-width: 300px;
                padding: 15px;
                border-radius: 5px;
                color: white;
                font-family: Arial, sans-serif;
            }}
            .alert-low {{ background-color: #17a2b8; }}
            .alert-medium {{ background-color: #ffc107; color: black; }}
            .alert-high {{ background-color: #fd7e14; }}
            .alert-critical {{ background-color: #dc3545; }}
            .alert-content button {{
                float: right;
                background: none;
                border: none;
                color: inherit;
                font-size: 18px;
                cursor: pointer;
            }}
        </style>
    </head>
    <body>
        <h1>Proctoring Monitor JavaScript</h1>
        <p>Copy the script below and include it in your exam frontend:</p>
        <pre><code>{FRONTEND_MONITORING_SCRIPT}</code></pre>
        
        <h2>Usage Example:</h2>
        <pre><code>
// Initialize proctoring monitor
const monitor = new ProctoringMonitor('your-exam-id', 'jwt-token');
        </code></pre>
    </body>
    </html>
    """, media_type="text/html")

@router.post("/test-detection")
async def test_detection_capabilities(
    test_image: UploadFile = File(...),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Test detection capabilities with a sample image (for debugging)"""
    token_data = verify_token(credentials.credentials)
    user = get_current_user(token_data)
    
    if user.role != UserRole.EXAMINER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Examiner access required"
        )
    
    try:
        image_data = await test_image.read()
        
        # Test detection without creating violations
        import cv2
        import numpy as np
        
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image")
        
        # Run all detection methods
        face_count, faces_info, face_confidence = proctoring_service._detect_faces_mediapipe(img)
        hands_count, hands_info, hands_confidence = proctoring_service._detect_hands_and_palms(img)
        detected_objects = proctoring_service._detect_objects_yolo(img)
        is_looking_away, gaze_confidence, gaze_info = proctoring_service._analyze_gaze_direction(img)
        
        return {
            "test_results": {
                "faces": {
                    "count": face_count,
                    "confidence": face_confidence,
                    "details": faces_info
                },
                "hands": {
                    "count": hands_count, 
                    "confidence": hands_confidence,
                    "details": hands_info
                },
                "objects": detected_objects,
                "gaze": {
                    "looking_away": is_looking_away,
                    "confidence": gaze_confidence,
                    "details": gaze_info
                }
            },
            "image_info": {
                "size": img.shape,
                "channels": img.shape[2] if len(img.shape) > 2 else 1
            }
        }
        
    except Exception as e:
        logger.error(f"Detection test failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Detection test failed: {str(e)}")

# Deprecated endpoint - kept for backward compatibility
@router.post("/monitor-frame")
async def monitor_frame_deprecated(
    exam_id: str,
    image: UploadFile = File(...),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Deprecated: Use /analyze-frame instead"""
    logger.warning("Deprecated endpoint /monitor-frame used, redirecting to /analyze-frame")
    return await analyze_webcam_frame(exam_id, image, credentials)


@router.post("/suspend")
async def suspend_exam(
    exam_id: str,
    student_id: str,
    reason: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Suspend an exam for a student, create a violation and notify examiner."""
    token_data = verify_token(credentials.credentials)
    user = get_current_user(token_data)

    # Allow students to trigger their own suspension events, examiners can also call
    if user.role == UserRole.STUDENT and user.id != student_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Students can only suspend their own exam")

    notification = proctoring_service.suspend_exam(exam_id, student_id, reason or "tab switch suspension")
    return {"message": "Exam suspended", "notification": notification}