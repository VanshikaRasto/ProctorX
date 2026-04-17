from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, List
import json
import logging
from datetime import datetime
from models.violation import ViolationCreate, ViolationType, ViolationSeverity
from services.proctoring_service import proctoring_service
from services.auth_service import verify_token, get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)

class ExaminerNotificationManager:
    """Manages WebSocket connections for examiners to receive real-time notifications"""
    def __init__(self):
        self.active_examiners: Dict[str, WebSocket] = {}  # examiner_id -> websocket
        self.examiner_exams: Dict[str, List[str]] = {}    # examiner_id -> list of exam_ids
    
    async def connect_examiner(self, websocket: WebSocket, examiner_id: str):
        await websocket.accept()
        self.active_examiners[examiner_id] = websocket
        if examiner_id not in self.examiner_exams:
            self.examiner_exams[examiner_id] = []
        logger.info(f"Examiner {examiner_id} connected for notifications")
    
    def disconnect_examiner(self, examiner_id: str):
        if examiner_id in self.active_examiners:
            del self.active_examiners[examiner_id]
        if examiner_id in self.examiner_exams:
            del self.examiner_exams[examiner_id]
        logger.info(f"Examiner {examiner_id} disconnected")
    
    async def send_notification(self, examiner_id: str, notification: dict):
        """Send notification to a specific examiner"""
        if examiner_id in self.active_examiners:
            websocket = self.active_examiners[examiner_id]
            try:
                await websocket.send_text(json.dumps(notification))
            except Exception as e:
                logger.error(f"Failed to send notification to examiner {examiner_id}: {e}")
    
    async def broadcast_notification(self, exam_id: str, notification: dict):
        """Broadcast notification to all examiners who own the exam"""
        for examiner_id, exams in self.examiner_exams.items():
            if exam_id in exams:
                await self.send_notification(examiner_id, notification)

examiner_notification_manager = ExaminerNotificationManager()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.student_exam_mapping: Dict[str, str] = {}
    
    async def connect(self, websocket: WebSocket, student_id: str, exam_id: str):
        await websocket.accept()
        self.active_connections[student_id] = websocket
        self.student_exam_mapping[student_id] = exam_id
        logger.info(f"Student {student_id} connected for exam {exam_id}")
    
    def disconnect(self, student_id: str):
        if student_id in self.active_connections:
            del self.active_connections[student_id]
        if student_id in self.student_exam_mapping:
            del self.student_exam_mapping[student_id]
        logger.info(f"Student {student_id} disconnected")
    
    async def send_message(self, student_id: str, message: dict):
        if student_id in self.active_connections:
            websocket = self.active_connections[student_id]
            await websocket.send_text(json.dumps(message))

manager = ConnectionManager()

@router.websocket("/ws/proctoring/{exam_id}")
async def websocket_proctoring_endpoint(
    websocket: WebSocket,
    exam_id: str,
    token: str = Query(...)
):
    """WebSocket endpoint for real-time proctoring monitoring"""
    try:
        # Verify token
        token_data = verify_token(token)
        user = get_current_user(token_data)
        
        if user.role.value != "STUDENT":
            await websocket.close(code=1000, reason="Only students can connect")
            return
        
        student_id = user.id
        await manager.connect(websocket, student_id, exam_id)
        
        try:
            while True:
                # Receive data from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different types of events
                await handle_proctoring_event(student_id, exam_id, message)
                
                # Send acknowledgment
                await manager.send_message(student_id, {
                    "type": "ack",
                    "timestamp": datetime.now().isoformat(),
                    "message": "Event processed"
                })
                
        except WebSocketDisconnect:
            manager.disconnect(student_id)
            logger.info(f"Student {student_id} disconnected from exam {exam_id}")
            
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        await websocket.close(code=1000, reason="Authentication failed")

async def handle_proctoring_event(student_id: str, exam_id: str, message: dict):
    """Handle different types of proctoring events"""
    event_type = message.get("type")
    timestamp = message.get("timestamp", datetime.now().isoformat())
    
    if event_type == "tab_switch":
        await handle_tab_switch_event(student_id, exam_id, message)
    elif event_type == "window_focus":
        await handle_window_focus_event(student_id, exam_id, message)
    elif event_type == "visibility_change":
        await handle_visibility_change_event(student_id, exam_id, message)
    elif event_type == "mouse_leave":
        await handle_mouse_leave_event(student_id, exam_id, message)
    elif event_type == "key_combination":
        await handle_key_combination_event(student_id, exam_id, message)
    else:
        logger.warning(f"Unknown event type: {event_type}")

async def handle_tab_switch_event(student_id: str, exam_id: str, message: dict):
    """Handle tab switch detection"""
    metadata = message.get("data", {})
    duration = metadata.get("duration", 0)
    
    # Determine severity based on duration
    if duration > 10:  # More than 10 seconds
        severity = ViolationSeverity.CRITICAL
    elif duration > 5:  # More than 5 seconds
        severity = ViolationSeverity.HIGH
    else:
        severity = ViolationSeverity.MEDIUM
    
    violation_data = ViolationCreate(
        exam_id=exam_id,
        student_id=student_id,
        type=ViolationType.TAB_SWITCH,
        severity=severity,
        description=f"Tab switch detected for {duration} seconds",
        metadata={
            "duration_seconds": duration,
            "timestamp": message.get("timestamp"),
            "page_visibility": metadata.get("page_visibility", "hidden")
        },
        confidence_score=1.0,  # Tab switch detection is highly reliable
        detection_method="JavaScript Visibility API"
    )
    
    proctoring_service.create_violation(violation_data)
    logger.info(f"Tab switch violation recorded for student {student_id}")

async def handle_window_focus_event(student_id: str, exam_id: str, message: dict):
    """Handle window focus loss events"""
    metadata = message.get("data", {})
    focus_lost_duration = metadata.get("focus_lost_duration", 0)
    
    if focus_lost_duration > 3:  # Only record if focus lost for more than 3 seconds
        violation_data = ViolationCreate(
            exam_id=exam_id,
            student_id=student_id,
            type=ViolationType.TAB_SWITCH,
            severity=ViolationSeverity.MEDIUM,
            description=f"Window focus lost for {focus_lost_duration} seconds",
            metadata={
                "focus_lost_duration": focus_lost_duration,
                "timestamp": message.get("timestamp"),
                "event_type": "window_blur"
            },
            confidence_score=0.9,
            detection_method="JavaScript Focus Events"
        )
        
        proctoring_service.create_violation(violation_data)
        logger.info(f"Window focus violation recorded for student {student_id}")

async def handle_visibility_change_event(student_id: str, exam_id: str, message: dict):
    """Handle page visibility change events"""
    metadata = message.get("data", {})
    visibility_state = metadata.get("visibility_state", "hidden")
    hidden_duration = metadata.get("hidden_duration", 0)
    
    if visibility_state == "hidden" and hidden_duration > 2:
        violation_data = ViolationCreate(
            exam_id=exam_id,
            student_id=student_id,
            type=ViolationType.TAB_SWITCH,
            severity=ViolationSeverity.HIGH,
            description=f"Page hidden for {hidden_duration} seconds",
            metadata={
                "visibility_state": visibility_state,
                "hidden_duration": hidden_duration,
                "timestamp": message.get("timestamp")
            },
            confidence_score=1.0,
            detection_method="Page Visibility API"
        )
        
        proctoring_service.create_violation(violation_data)
        logger.info(f"Page visibility violation recorded for student {student_id}")

async def handle_mouse_leave_event(student_id: str, exam_id: str, message: dict):
    """Handle mouse leaving exam area"""
    metadata = message.get("data", {})
    leave_duration = metadata.get("leave_duration", 0)
    
    # Only record if mouse left for significant duration
    if leave_duration > 5:
        violation_data = ViolationCreate(
            exam_id=exam_id,
            student_id=student_id,
            type=ViolationType.EYE_MOVEMENT,  # Using eye movement as proxy for attention
            severity=ViolationSeverity.LOW,
            description=f"Mouse left exam area for {leave_duration} seconds",
            metadata={
                "leave_duration": leave_duration,
                "timestamp": message.get("timestamp"),
                "event_type": "mouse_leave"
            },
            confidence_score=0.7,
            detection_method="JavaScript Mouse Events"
        )
        
        proctoring_service.create_violation(violation_data)
        logger.info(f"Mouse leave violation recorded for student {student_id}")

async def handle_key_combination_event(student_id: str, exam_id: str, message: dict):
    """Handle suspicious key combinations"""
    metadata = message.get("data", {})
    key_combination = metadata.get("keys", [])
    
    # Suspicious key combinations
    suspicious_combinations = [
        ["alt", "tab"],
        ["ctrl", "c"],
        ["ctrl", "v"],
        ["ctrl", "shift", "i"],  # Developer tools
        ["f12"],  # Developer tools
        ["ctrl", "shift", "c"],  # Inspect element
        ["ctrl", "u"],  # View source
        ["alt", "f4"],  # Close window
    ]
    
    key_combo_str = "+".join(sorted(key_combination))
    
    for suspicious_combo in suspicious_combinations:
        if set(key_combination) == set(suspicious_combo):
            severity = ViolationSeverity.HIGH if "ctrl" in key_combination else ViolationSeverity.MEDIUM
            
            violation_data = ViolationCreate(
                exam_id=exam_id,
                student_id=student_id,
                type=ViolationType.TAB_SWITCH,
                severity=severity,
                description=f"Suspicious key combination detected: {key_combo_str}",
                metadata={
                    "key_combination": key_combination,
                    "timestamp": message.get("timestamp"),
                    "event_type": "key_combination"
                },
                confidence_score=0.95,
                detection_method="JavaScript Keyboard Events"
            )
            
            proctoring_service.create_violation(violation_data)
            logger.info(f"Key combination violation recorded for student {student_id}: {key_combo_str}")
            break

@router.websocket("/ws/examiner-notifications/{examiner_id}")
async def websocket_examiner_notifications(
    websocket: WebSocket,
    examiner_id: str,
    token: str = Query(...)
):
    """WebSocket endpoint for examiners to receive real-time suspension notifications"""
    try:
        # Verify token
        token_data = verify_token(token)
        user = get_current_user(token_data)
        
        if user.role.value != "EXAMINER" or user.id != examiner_id:
            await websocket.close(code=1000, reason="Examiner access required")
            return
        
        await examiner_notification_manager.connect_examiner(websocket, examiner_id)
        
        try:
            while True:
                # Keep connection alive, receive ping/heartbeat from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Optionally update examiner's exam list if sent by client
                if message.get("type") == "register_exam":
                    exam_id = message.get("exam_id")
                    if exam_id and exam_id not in examiner_notification_manager.examiner_exams[examiner_id]:
                        examiner_notification_manager.examiner_exams[examiner_id].append(exam_id)
                        logger.info(f"Examiner {examiner_id} registered for exam {exam_id}")
                
        except WebSocketDisconnect:
            examiner_notification_manager.disconnect_examiner(examiner_id)
            logger.info(f"Examiner {examiner_id} disconnected from notifications")
            
    except Exception as e:
        logger.error(f"Examiner WebSocket error: {str(e)}")
        await websocket.close(code=1000, reason="Authentication failed")

@router.get("/ws/active-connections")
async def get_active_connections():
    """Get list of active WebSocket connections (for monitoring)"""
    return {
        "active_connections": len(manager.active_connections),
        "students": list(manager.active_connections.keys()),
        "exam_mappings": manager.student_exam_mapping
    }

@router.post("/ws/send-alert/{student_id}")
async def send_alert_to_student(
    student_id: str,
    alert_message: dict,
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    """Send alert message to specific student via WebSocket"""
    token_data = verify_token(credentials.credentials)
    user = get_current_user(token_data)
    
    if user.role.value != "EXAMINER":
        raise HTTPException(status_code=403, detail="Examiner access required")
    
    if student_id in manager.active_connections:
        await manager.send_message(student_id, {
            "type": "alert",
            "message": alert_message.get("message", "Proctoring alert"),
            "severity": alert_message.get("severity", "medium"),
            "timestamp": datetime.now().isoformat()
        })
        return {"message": "Alert sent successfully"}
    else:
        raise HTTPException(status_code=404, detail="Student not connected")

# JavaScript code to be included in the frontend for real-time monitoring
FRONTEND_MONITORING_SCRIPT = '''
// Real-time proctoring monitoring script
class ProctoringMonitor {
    constructor(examId, token) {
        this.examId = examId;
        this.token = token;
        this.websocket = null;
        this.isPageVisible = true;
        this.visibilityStartTime = null;
        this.focusStartTime = null;
        this.mouseInArea = true;
        this.mouseLeaveTime = null;
        
        this.init();
    }
    
    init() {
        this.connectWebSocket();
        this.setupEventListeners();
    }
    
    connectWebSocket() {
        const wsUrl = `ws://localhost:8000/api/v1/proctoring/ws/proctoring/${this.examId}?token=${this.token}`;
        this.websocket = new WebSocket(wsUrl);
        
        this.websocket.onopen = () => {
            console.log('Proctoring WebSocket connected');
        };
        
        this.websocket.onmessage = (event) => {
            const message = JSON.parse(event.data);
            this.handleWebSocketMessage(message);
        };
        
        this.websocket.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
        
        this.websocket.onclose = () => {
            console.log('WebSocket connection closed');
            // Attempt to reconnect after 3 seconds
            setTimeout(() => this.connectWebSocket(), 3000);
        };
    }
    
    setupEventListeners() {
        // Page visibility change
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.visibilityStartTime = Date.now();
                this.isPageVisible = false;
            } else {
                if (this.visibilityStartTime) {
                    const duration = (Date.now() - this.visibilityStartTime) / 1000;
                    this.sendEvent('visibility_change', {
                        visibility_state: 'visible',
                        hidden_duration: duration
                    });
                }
                this.isPageVisible = true;
                this.visibilityStartTime = null;
            }
        });
        
        // Window focus/blur
        window.addEventListener('blur', () => {
            this.focusStartTime = Date.now();
        });
        
        window.addEventListener('focus', () => {
            if (this.focusStartTime) {
                const duration = (Date.now() - this.focusStartTime) / 1000;
                this.sendEvent('window_focus', {
                    focus_lost_duration: duration
                });
                this.focusStartTime = null;
            }
        });
        
        // Mouse leave/enter exam area
        document.addEventListener('mouseleave', () => {
            this.mouseLeaveTime = Date.now();
            this.mouseInArea = false;
        });
        
        document.addEventListener('mouseenter', () => {
            if (this.mouseLeaveTime) {
                const duration = (Date.now() - this.mouseLeaveTime) / 1000;
                this.sendEvent('mouse_leave', {
                    leave_duration: duration
                });
                this.mouseLeaveTime = null;
            }
            this.mouseInArea = true;
        });
        
        // Suspicious key combinations
        document.addEventListener('keydown', (event) => {
            const keys = [];
            if (event.ctrlKey) keys.push('ctrl');
            if (event.altKey) keys.push('alt');
            if (event.shiftKey) keys.push('shift');
            if (event.metaKey) keys.push('meta');
            
            // Add the main key
            if (event.key !== 'Control' && event.key !== 'Alt' && event.key !== 'Shift' && event.key !== 'Meta') {
                keys.push(event.key.toLowerCase());
            }
            
            if (keys.length > 1) {
                this.sendEvent('key_combination', {
                    keys: keys
                });
            }
        });
        
        // Detect Alt+Tab (more complex detection)
        let altPressed = false;
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Alt') {
                altPressed = true;
            }
            if (altPressed && event.key === 'Tab') {
                event.preventDefault(); // Try to prevent Alt+Tab
                this.sendEvent('tab_switch', {
                    duration: 1 // Immediate detection
                });
            }
        });
        
        document.addEventListener('keyup', (event) => {
            if (event.key === 'Alt') {
                altPressed = false;
            }
        });
    }
    
    sendEvent(type, data) {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            const message = {
                type: type,
                data: data,
                timestamp: new Date().toISOString()
            };
            this.websocket.send(JSON.stringify(message));
        }
    }
    
    handleWebSocketMessage(message) {
        if (message.type === 'alert') {
            // Show alert to user
            this.showAlert(message.message, message.severity);
        }
    }
    
    showAlert(message, severity) {
        // Create and show alert notification
        const alertDiv = document.createElement('div');
        alertDiv.className = `proctoring-alert alert-${severity}`;
        alertDiv.innerHTML = `
            <div class="alert-content">
                <strong>Proctoring Alert:</strong> ${message}
                <button onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
        `;
        document.body.appendChild(alertDiv);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (alertDiv.parentElement) {
                alertDiv.remove();
            }
        }, 5000);
    }
}

// Initialize monitoring when page loads
// Usage: new ProctoringMonitor('exam_id_here', 'jwt_token_here');
'''