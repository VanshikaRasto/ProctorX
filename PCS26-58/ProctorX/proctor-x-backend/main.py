# main.py
# Import necessary FastAPI components for web framework functionality
from fastapi import FastAPI, HTTPException, Depends, status
# Import CORS middleware to handle cross-origin requests from frontend
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer

# Import ASGI server for running the FastAPI application
import uvicorn
# Import logging for application monitoring and debugging
import logging
from datetime import datetime
import os
import json
from typing import List, Optional

# Import API route handlers for different functional modules
from routers import auth, exams, students, results, proctoring, monitoring, registrations
# Import enhanced WebSocket-based proctoring router for real-time monitoring
from routers import websocket_proctoring
# Import authentication service for token verification
from services.auth_service import verify_token
# Import user-related models and enums
from models.user import UserRole, User, UserStatus

# Try to import exam models with error handling for graceful degradation
# This allows the application to run even if exam models are not available
try:
    from models.exam import (
        Exam,           # Main exam model
        ExamCreate,     # Model for creating new exams
        ExamAssignment, # Model for exam assignments
        ExamStatus,     # Enum for exam statuses
        parse_mcq_questions_debug,  # Utility function for parsing MCQ questions
        create_exam_from_file       # Utility function for creating exams from files
    )
    EXAM_MODELS_AVAILABLE = True
except ImportError:
    # Create basic fallback models if exam.py doesn't exist
    # This ensures the API can start even without full exam functionality
    from pydantic import BaseModel
    from enum import Enum
    
    class ExamType(str, Enum):
        MCQ = "mcq"
        SUBJECTIVE = "subjective"
    
    class ExamStatus(str, Enum):
        DRAFT = "draft"
        ACTIVE = "active"
        COMPLETED = "completed"
        ARCHIVED = "archived"
    
    class ExamCreate(BaseModel):
        title: str
        description: str
        exam_type: ExamType
        duration_minutes: int
        file_content: str
    
    EXAM_MODELS_AVAILABLE = False

# Enhanced AI Proctoring: Check availability of AI libraries for advanced monitoring
# This section dynamically detects which AI/ML libraries are installed
AI_PROCTORING_AVAILABLE = False
AI_CAPABILITIES = []

# Check for OpenCV availability - essential for image processing and computer vision
try:
    import cv2
    AI_CAPABILITIES.append("OpenCV")
    AI_PROCTORING_AVAILABLE = True
except ImportError:
    pass

# Check for YOLO (You Only Look Once) - advanced object detection
try:
    from ultralytics import YOLO
    AI_CAPABILITIES.append("YOLO")
    AI_PROCTORING_AVAILABLE = True
except ImportError:
    pass

# Check for CVZone - simplified computer vision functions
try:
    import cvzone
    AI_CAPABILITIES.append("CVZone")  
    AI_PROCTORING_AVAILABLE = True
except ImportError:
    pass

# Check for MTCNN - Multi-task Cascaded Convolutional Networks for face detection
try:
    from mtcnn import MTCNN
    AI_CAPABILITIES.append("MTCNN")
    AI_PROCTORING_AVAILABLE = True
except ImportError:
    pass

# MediaPipe is optional - Google's framework for building multimodal perception pipelines
try:
    import mediapipe as mp
    AI_CAPABILITIES.append("MediaPipe")
except ImportError:
    pass

if AI_PROCTORING_AVAILABLE:
    logger_ai = logging.getLogger("ai_proctoring")
    logger_ai.info(f"AI proctoring libraries loaded: {', '.join(AI_CAPABILITIES)}")
else:
    print("Warning: No AI proctoring libraries available")
    print("Install with: pip install ultralytics cvzone mtcnn")

# Configure logging with DEBUG level for detailed application monitoring
# This helps in troubleshooting and monitoring application behavior
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for detailed logging during development
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/logs/app.log'),  # Log to file for persistence
        logging.StreamHandler()                   # Log to console for real-time monitoring
    ]
)

# Create main application logger
logger = logging.getLogger(__name__)

# Create necessary data directories for application functionality
# These directories store different types of application data
directories = [
    'data/users',      # User account information and profiles
    'data/exams',      # Exam definitions and configurations
    'data/submissions', # Student exam submissions and answers
    'data/results',     # Processed exam results and scores
    'data/violations',  # Proctoring violation records and evidence
    'data/logs',        # Application log files
    'data/models',      # AI/ML model files and caches
    'data/temp'         # Temporary files for processing
]

# Create directories if they don't exist
# This ensures the application has all required storage locations
for directory in directories:
    os.makedirs(directory, exist_ok=True)

# Initialize FastAPI application with metadata
app = FastAPI(
    title="Online Exam Proctoring Platform",
    description="A secure platform for conducting proctored online exams with Enhanced AI Detection",
    version="2.0.0"  # Updated version to reflect enhanced AI features
)

# Configure CORS (Cross-Origin Resource Sharing) middleware
# This allows the frontend application (running on localhost:3000) to communicate with the backend API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,                   # Allow cookies and authentication headers
    allow_methods=["*"],                      # Allow all HTTP methods
    allow_headers=["*"],                      # Allow all headers
)

# Initialize HTTP Bearer token security for API authentication
security = HTTPBearer()

# Simplified authentication dependency for testing and development
# In production, this should be replaced with proper JWT token validation
async def get_current_user_simple(token: str = Depends(security)) -> User:
    """Simplified auth for testing - replace with your actual auth logic"""
    try:
        # Try to use the existing authentication service
        from services.auth_service import get_current_user
        return await get_current_user(token)
    except:
        # Fallback: create a dummy user for testing purposes
        # This allows the API to function during development
        logger.warning("Using dummy auth - replace with real auth")
        return User(
            id="test_user_123",
            email="test@example.com",
            username="test_examiner",
            full_name="Test Examiner",
            role=UserRole.EXAMINER,
            status=UserStatus.ACTIVE,
            created_at=datetime.now(),
            last_login=datetime.now()
        )

# Include all API routers with their respective prefixes and tags
# This organizes the API endpoints into logical groups
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(exams.router, prefix="/api/exams", tags=["Exams"])  # Handles all exam-related endpoints
app.include_router(students.router, prefix="/api/students", tags=["Students"])
app.include_router(results.router, prefix="/api/results", tags=["Results"])

# Keep existing proctoring router for backward compatibility
app.include_router(proctoring.router, prefix="/api/proctoring", tags=["Proctoring"])

# Enhanced AI Proctoring: Include WebSocket-based real-time monitoring router
# This provides advanced proctoring capabilities with real-time detection
try:
    from routers import websocket_proctoring
    app.include_router(
        websocket_proctoring.router, 
        prefix="/api/v1/proctoring", 
        tags=["🔴 Real-time Monitoring"]
    )
except ImportError:
    logger.warning("WebSocket proctoring router not available")

# Include remaining system routers
app.include_router(monitoring.router, prefix="/api/monitoring", tags=["System Monitoring"])
app.include_router(registrations.router, prefix="/api/registrations", tags=["Registrations"])

# Startup event handler - initializes AI models and services when the application starts
@app.on_event("startup")
async def startup_event():
    """Initialize AI models and services on startup"""
    logger.info("Starting Enhanced AI Proctoring Platform...")
    
    if AI_PROCTORING_AVAILABLE:
        try:
            # Initialize the enhanced proctoring service
            from services.proctoring_service import proctoring_service
            
            logger.info("Initializing AI detection models...")
            
            # Check what AI models are actually available in the service
            capabilities = {
                "opencv": proctoring_service.face_cascade is not None,
                "enhanced_opencv_hands": getattr(proctoring_service, 'enhanced_opencv_hands', False),
                "deepface": getattr(proctoring_service, 'deepface_available', False),
                "yolo": getattr(proctoring_service, 'yolo_available', False),
                "mtcnn": getattr(proctoring_service, 'mtcnn_available', False)
            }
            
            # Count active AI models
            active_models = sum(1 for status in capabilities.values() if status)
            logger.info(f"AI Proctoring initialized with {active_models}/4 models active")
            logger.info(f"Available capabilities: {', '.join([k for k, v in capabilities.items() if v])}")
            
            # Determine detection mode based on available models
            if active_models >= 2:
                logger.info("Enhanced detection mode enabled")
            elif active_models >= 1:
                logger.info("Basic detection mode enabled")
            else:
                logger.warning("Limited detection capabilities")
                
        except Exception as e:
            logger.error(f"AI Proctoring initialization failed: {str(e)}")
    else:
        logger.warning("Enhanced AI Proctoring disabled - no AI libraries found")
        logger.info("Install with: pip install ultralytics cvzone mtcnn")

# Root endpoint - provides basic API information and status
@app.get("/")
async def root():
    """Root endpoint returning API information"""
    return {
        "message": "Online Exam Proctoring Platform API",
        "version": "2.0.0",
        "features": {
            "enhanced_ai_proctoring": AI_PROCTORING_AVAILABLE,
            "real_time_monitoring": True,
            "websocket_support": True
        },
        "timestamp": datetime.now().isoformat()
    }

# Health check endpoint - monitors API status and availability
@app.get("/api/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "exam-proctoring-api",
        "version": "2.0.0",
        "ai_proctoring_enabled": AI_PROCTORING_AVAILABLE
    }

# Enhanced AI Proctoring: Health check specifically for AI capabilities
@app.get("/api/ai-health", tags=["🤖 AI Status"])
async def ai_health_check():
    """Check AI proctoring capabilities and model status"""
    if not AI_PROCTORING_AVAILABLE:
        return {
            "status": "disabled",
            "message": "AI libraries not installed",
            "install_command": "pip install opencv-python mediapipe ultralytics"
        }
    
    try:
        from services.proctoring_service import proctoring_service
        
        # Test AI model status
        ai_status = {
            "mediapipe_face": proctoring_service.face_detection is not None,
            "mediapipe_hands": proctoring_service.hands is not None,
            "mediapipe_face_mesh": proctoring_service.face_mesh is not None,
            "yolo_object_detection": proctoring_service.yolo_model is not None,
            "opencv_fallback": proctoring_service.face_cascade is not None
        }
        
        active_models = sum(1 for status in ai_status.values() if status)
        
        return {
            "status": "healthy" if active_models >= 3 else "degraded",
            "active_models": active_models,
            "total_models": 5,
            "models": ai_status,
            "capabilities": [
                "face_detection",
                "hand_palm_detection",
                "gaze_direction_analysis", 
                "object_detection",
                "real_time_websocket_monitoring"
            ],
            "detection_confidence": "high" if active_models >= 4 else "medium" if active_models >= 2 else "low",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"AI health check failed: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }

# Test endpoint for parser (keeping this as it's useful for debugging)
@app.get("/api/test-parser", tags=["Debug"])
async def test_parser_endpoint():
    """
    Test endpoint to verify the parser is working.
    """
    try:
        # Test content
        test_content = """QUESTION_ID: q1
TYPE: mcq
POINTS: 2
QUESTION: What is the capital of France?
OPTIONS:
A) London
B) Berlin
C) Paris
D) Madrid
CORRECT: C"""
        
        if not EXAM_MODELS_AVAILABLE:
            return {
                "status": "error",
                "message": "Parser functions not available - please create models/exam.py with parser functions"
            }
        
        questions = parse_mcq_questions_debug(test_content)
        return {
            "status": "success",
            "questions_parsed": len(questions),
            "message": "Parser is working correctly",
            "questions": [
                {
                    "id": q.id,
                    "question": q.question[:50] + "..." if len(q.question) > 50 else q.question,
                    "options_count": len(q.options) if q.options else 0,
                    "points": q.points,
                    "correct_answer": q.correct_answer
                }
                for q in questions
            ]
        }
        
    except Exception as e:
        logger.error(f"Parser test failed: {str(e)}")
        return {"status": "error", "message": str(e)}

# Enhanced AI Proctoring: Test endpoint for AI detection
@app.get("/api/test-ai-detection", tags=["🤖 AI Testing"])
async def test_ai_detection():
    """Test AI detection capabilities"""
    if not AI_PROCTORING_AVAILABLE:
        return {
            "status": "disabled",
            "message": "AI proctoring libraries not available",
            "install_command": "pip install opencv-python mediapipe ultralytics"
        }
    
    try:
        import cv2
        import numpy as np
        from services.proctoring_service import proctoring_service
        
        # Create a test image
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        test_image[:] = (100, 150, 200)  # Fill with color
        
        # Test each detection method
        results = {}
        
        # Test face detection
        try:
            face_count, faces_info, face_confidence = proctoring_service._detect_faces_mediapipe(test_image)
            results["face_detection"] = {
                "status": "working",
                "faces_detected": face_count,
                "confidence": face_confidence
            }
        except Exception as e:
            results["face_detection"] = {"status": "error", "error": str(e)}
        
        # Test hand detection
        try:
            hands_count, hands_info, hands_confidence = proctoring_service._detect_hands_and_palms(test_image)
            results["hand_detection"] = {
                "status": "working", 
                "hands_detected": hands_count,
                "confidence": hands_confidence
            }
        except Exception as e:
            results["hand_detection"] = {"status": "error", "error": str(e)}
        
        # Test YOLO object detection
        try:
            detected_objects = proctoring_service._detect_objects_yolo(test_image)
            results["object_detection"] = {
                "status": "working",
                "objects_detected": len(detected_objects)
            }
        except Exception as e:
            results["object_detection"] = {"status": "error", "error": str(e)}
        
        # Test gaze detection
        try:
            is_looking_away, gaze_confidence, gaze_info = proctoring_service._analyze_gaze_direction(test_image)
            results["gaze_detection"] = {
                "status": "working",
                "looking_away": is_looking_away,
                "confidence": gaze_confidence
            }
        except Exception as e:
            results["gaze_detection"] = {"status": "error", "error": str(e)}
        
        working_detectors = sum(1 for r in results.values() if r.get("status") == "working")
        
        return {
            "status": "success",
            "working_detectors": f"{working_detectors}/4",
            "overall_health": "excellent" if working_detectors == 4 else "good" if working_detectors >= 3 else "needs_attention",
            "detection_results": results,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"AI detection test failed: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }

# Additional utility endpoints
@app.get("/api/system/status", tags=["System"])
async def system_status():
    """Get system status and configuration"""
    return {
        "status": "running",
        "version": "2.0.0",
        "exam_models_available": EXAM_MODELS_AVAILABLE,
        "ai_proctoring_available": AI_PROCTORING_AVAILABLE,
        "directories": {
            "users": os.path.exists("data/users"),
            "exams": os.path.exists("data/exams"),
            "submissions": os.path.exists("data/submissions"),
            "results": os.path.exists("data/results"),
            "violations": os.path.exists("data/violations"),
            "logs": os.path.exists("data/logs"),
            "models": os.path.exists("data/models"),  # New AI models directory
            "temp": os.path.exists("data/temp")       # New temp processing directory
        },
        "features": {
            "enhanced_ai_proctoring": AI_PROCTORING_AVAILABLE,
            "real_time_websockets": True,
            "multi_detection_types": True,
            "confidence_scoring": True
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/system/files", tags=["System"])
async def list_system_files():
    """List files in data directories (for debugging)"""
    try:
        file_info = {}
        
        # Include new AI-related directories
        directories = ["users", "exams", "submissions", "results", "violations", "models", "temp"]
        
        for directory in directories:
            dir_path = f"data/{directory}"
            if os.path.exists(dir_path):
                files = os.listdir(dir_path)
                file_info[directory] = {
                    "count": len(files),
                    "files": files[:10]  # Limit to first 10 files
                }
            else:
                file_info[directory] = {"count": 0, "files": []}
        
        return file_info
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        return {"error": str(e)}

@app.get("/api/debug/available-exams", tags=["Debug"])
async def debug_available_exams():
    """Debug endpoint to test available exams functionality"""
    try:
        from services.registration_service import registration_service
        from services.exam_service import exam_service
        
        # Test with a dummy student ID
        test_student_id = "test_student_123"
        
        # Get all active exams
        all_active_exams = exam_service.get_all_active_exams()
        
        # Get available exams for the test student
        available_exams = registration_service.get_available_exams(test_student_id)
        
        return {
            "status": "success",
            "test_student_id": test_student_id,
            "total_active_exams": len(all_active_exams),
            "active_exams": [
                {
                    "id": exam.id,
                    "title": exam.title,
                    "status": exam.status.value if hasattr(exam.status, 'value') else str(exam.status),
                    "created_by": exam.created_by
                }
                for exam in all_active_exams
            ],
            "available_exams_count": len(available_exams),
            "available_exams": available_exams[:3] if available_exams else [],  # Show first 3 for brevity
            "registration_service_working": True
        }
        
    except Exception as e:
        logger.error(f"Debug available exams failed: {str(e)}")
        return {
            "status": "error", 
            "error": str(e),
            "registration_service_working": False
        }

# Enhanced AI Proctoring: WebSocket connection status
@app.get("/api/websocket-status", tags=["🔴 WebSocket Status"])
async def websocket_status():
    """Get WebSocket connection status for real-time monitoring"""
    try:
        from routers.websocket_proctoring import manager
        
        return {
            "status": "healthy",
            "active_connections": len(manager.active_connections),
            "connected_students": list(manager.active_connections.keys()),
            "exam_mappings": dict(manager.student_exam_mapping),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "active_connections": 0,
            "timestamp": datetime.now().isoformat()
        }

# Entry point for running the application directly
# This allows the server to be started with: python main.py
if __name__ == "__main__":
    uvicorn.run(
        "main:app",           # Reference to the FastAPI app instance
        host="0.0.0.0",       # Listen on all network interfaces
        port=8000,            # Standard port for development
        reload=True,          # Enable auto-reload during development
        log_level="debug"     # Set logging level to debug
    )