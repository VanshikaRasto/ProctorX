import json
import os
import uuid
import cv2
import numpy as np
from datetime import datetime
from typing import List, Optional, Tuple
from fastapi import HTTPException
from models.violation import Violation, ViolationCreate, ViolationType, ViolationSeverity
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProctoringService:
    def __init__(self):
        self.violations_file = "data/violations/violations.json"
        self.phone_tracking_file = "data/violations/phone_tracking.json"
        self._ensure_violations_file()
        self._ensure_phone_tracking_file()

        logger.info("Initializing Enhanced Proctoring Service...")

        # ── OpenCV face detection ──────────────────────────────────────────────
        self.opencv_available = False
        try:
            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
            self.eye_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_eye.xml"
            )
            if not self.face_cascade.empty():
                self.opencv_available = True
                logger.info("✓ OpenCV face detection loaded")
            else:
                logger.error("OpenCV cascade files not found")
                self.face_cascade = None
                self.eye_cascade = None
        except Exception as e:
            logger.error(f"OpenCV initialization failed: {e}")
            self.face_cascade = None
            self.eye_cascade = None

        # ── DeepFace ──────────────────────────────────────────────────────────
        self.deepface_available = False
        try:
            from deepface import DeepFace as _DeepFace

            self._DeepFace = _DeepFace
            test_img = np.zeros((100, 100, 3), dtype=np.uint8)
            _DeepFace.extract_faces(test_img, enforce_detection=False)
            self.deepface_available = True
            logger.info("✓ DeepFace face detection loaded")
        except Exception as e:
            logger.warning(f"DeepFace not available: {e}")
            self._DeepFace = None

        # ── Enhanced OpenCV hand detection ────────────────────────────────────
        self.enhanced_opencv_hands = self.opencv_available
        if self.enhanced_opencv_hands:
            logger.info("✓ Enhanced OpenCV hand detection available")

        # ── YOLO object detection ─────────────────────────────────────────────
        self.yolo_available = False
        self.yolo_model = None
        try:
            from ultralytics import YOLO

            self.yolo_model = YOLO("yolov8n.pt")
            test_img = np.zeros((100, 100, 3), dtype=np.uint8)
            self.yolo_model(test_img, conf=0.5, verbose=False)
            self.yolo_available = True
            logger.info("✓ YOLO object detection loaded and tested")
        except Exception as e:
            logger.warning(f"YOLO not available: {e}")

        # MTCNN intentionally skipped (TensorFlow compatibility issues)
        self.mtcnn_available = False
        logger.info("Skipping MTCNN (TensorFlow compatibility issues)")

        capabilities = []
        if self.opencv_available:
            capabilities.append("OpenCV")
        if self.enhanced_opencv_hands:
            capabilities.append("Enhanced OpenCV Hands")
        if self.deepface_available:
            capabilities.append("DeepFace")
        if self.yolo_available:
            capabilities.append("YOLO Objects")

        self.enhanced_available = (
            self.yolo_available or self.enhanced_opencv_hands or self.deepface_available
        )

        logger.info(
            f"Proctoring capabilities: {', '.join(capabilities) if capabilities else 'Basic only'}"
        )
        logger.info(
            f"Enhanced detection: {'enabled' if self.enhanced_available else 'basic mode'}"
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Persistence helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _ensure_violations_file(self):
        if not os.path.exists(self.violations_file):
            os.makedirs("data/violations", exist_ok=True)
            with open(self.violations_file, "w") as f:
                json.dump({}, f)

    def _ensure_phone_tracking_file(self):
        """Ensure phone tracking file exists for monitoring high-confidence phone detections"""
        if not os.path.exists(self.phone_tracking_file):
            os.makedirs("data/violations", exist_ok=True)
            with open(self.phone_tracking_file, "w") as f:
                json.dump({}, f)

    def _load_violations(self) -> dict:
        try:
            with open(self.violations_file, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_violations(self, violations: dict):
        with open(self.violations_file, "w") as f:
            json.dump(violations, f, indent=2, default=str)

    def _load_phone_tracking(self) -> dict:
        """Load phone tracking data for high-confidence detections"""
        try:
            with open(self.phone_tracking_file, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_phone_tracking(self, phone_tracking: dict):
        """Save phone tracking data"""
        with open(self.phone_tracking_file, "w") as f:
            json.dump(phone_tracking, f, indent=2, default=str)

    def _track_phone_detection(self, exam_id: str, student_id: str, confidence: float):
        """
        Track high-confidence phone detections and check if threshold is exceeded.
        
        Args:
            exam_id: Exam identifier
            student_id: Student identifier  
            confidence: Detection confidence score (0.0-1.0)
            
        Returns:
            dict: Tracking result including whether exam should be revoked
        """
        logger.info(f"Tracking phone detection: exam_id={exam_id}, student_id={student_id}, confidence={confidence:.2f}")
        
        # Only track detections with confidence above 60%
        if confidence < 0.60:
            logger.debug(f"Confidence {confidence:.2f} below threshold 0.60, not tracking")
            return {"should_revoke": False, "count": 0, "threshold_exceeded": False}
            
        phone_tracking = self._load_phone_tracking()
        tracking_key = f"{exam_id}_{student_id}"
        
        # Initialize tracking for this exam/student if not exists
        if tracking_key not in phone_tracking:
            phone_tracking[tracking_key] = {
                "exam_id": exam_id,
                "student_id": student_id,
                "high_confidence_detections": [],
                "first_detection": datetime.now().isoformat(),
                "exam_revoked": False
            }
        
        tracking_data = phone_tracking[tracking_key]
        
        # Skip if exam already revoked
        if tracking_data.get("exam_revoked", False):
            logger.info(f"Exam already revoked for {tracking_key}, current count: {len(tracking_data['high_confidence_detections'])}")
            return {"should_revoke": False, "count": len(tracking_data["high_confidence_detections"]), "threshold_exceeded": True}
        
        # Add this detection
        detection_entry = {
            "timestamp": datetime.now().isoformat(),
            "confidence": confidence,
            "detection_id": str(uuid.uuid4())
        }
        tracking_data["high_confidence_detections"].append(detection_entry)
        
        # Check if threshold exceeded (more than 3 detections)
        detection_count = len(tracking_data["high_confidence_detections"])
        threshold = 3
        threshold_exceeded = detection_count > threshold
        
        logger.info(f"Phone detection count: {detection_count}, threshold: {threshold}, exceeded: {threshold_exceeded}")
        
        if threshold_exceeded:
            tracking_data["exam_revoked"] = True
            tracking_data["revocation_timestamp"] = datetime.now().isoformat()
            tracking_data["revocation_reason"] = f"More than {threshold} phone detections with confidence > 60%"
            
            logger.error(f"PHONE THRESHOLD EXCEEDED: {detection_count} high-confidence phone detections detected for student {student_id} in exam {exam_id}")
        
        # Save updated tracking data
        phone_tracking[tracking_key] = tracking_data
        self._save_phone_tracking(phone_tracking)
        
        result = {
            "should_revoke": threshold_exceeded,
            "count": detection_count,
            "threshold": threshold,
            "threshold_exceeded": threshold_exceeded,
            "detections": tracking_data["high_confidence_detections"]
        }
        
        logger.info(f"Phone tracking result: {result}")
        return result

    # ──────────────────────────────────────────────────────────────────────────
    # Violation CRUD
    # ──────────────────────────────────────────────────────────────────────────

    def create_violation(self, violation_data: ViolationCreate) -> Violation:
        violations = self._load_violations()
        violation_id = str(uuid.uuid4())
        
        # Try to get student name from user data
        student_name = ""
        try:
            from services.auth_service import auth_service
            user = auth_service.get_user_by_id(violation_data.student_id)
            if user:
                student_name = user.full_name
        except Exception as e:
            logger.debug(f"Could not fetch student name for {violation_data.student_id}: {e}")
        
        violation = Violation(
            id=violation_id,
            exam_id=violation_data.exam_id,
            student_id=violation_data.student_id,
            student_name=student_name,
            type=violation_data.type,
            severity=violation_data.severity,
            description=violation_data.description,
            timestamp=datetime.now(),
            metadata=violation_data.metadata or {},
            confidence_score=getattr(violation_data, "confidence_score", None),
            detection_method=getattr(violation_data, "detection_method", "OpenCV"),
        )
        violations[violation_id] = violation.dict()
        self._save_violations(violations)
        logger.info(
            f"VIOLATION CREATED: {violation_data.type.value} for student {violation_data.student_id}"
        )
        return violation

    # ──────────────────────────────────────────────────────────────────────────
    # Detection methods
    # ──────────────────────────────────────────────────────────────────────────

    def _detect_faces(self, image: np.ndarray) -> Tuple[int, List[dict], float]:
        """
        Detect faces. Uses DeepFace when available, falls back to OpenCV Haar cascades.
        Returns (count, faces_info, max_confidence).
        """
        # ── Try DeepFace first ────────────────────────────────────────────────
        if self.deepface_available and self._DeepFace is not None:
            try:
                rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                results = self._DeepFace.extract_faces(
                    rgb, enforce_detection=False, detector_backend="opencv"
                )
                faces_info = []
                max_confidence = 0.0
                for face in results:
                    conf = face.get("confidence", 0.7)
                    region = face.get("facial_area", {})
                    x = region.get("x", 0)
                    y = region.get("y", 0)
                    w = region.get("w", 0)
                    h = region.get("h", 0)
                    if w == 0 or h == 0:
                        continue
                    max_confidence = max(max_confidence, conf)
                    faces_info.append(
                        {"bbox": [x, y, w, h], "confidence": conf, "method": "DeepFace"}
                    )
                logger.debug(f"DeepFace detected {len(faces_info)} faces")
                return len(faces_info), faces_info, max_confidence
            except Exception as e:
                logger.warning(f"DeepFace face detection failed, falling back to OpenCV: {e}")

        # ── OpenCV Haar cascade fallback ──────────────────────────────────────
        return self._detect_faces_opencv(image)

    def _detect_faces_opencv(self, image: np.ndarray) -> Tuple[int, List[dict], float]:
        """Detect faces using OpenCV Haar cascades."""
        faces_info = []
        max_confidence = 0.0

        if not self.opencv_available or self.face_cascade is None:
            logger.warning("Face detection not available")
            return 0, [], 0.0

        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30),
                flags=cv2.CASCADE_SCALE_IMAGE,
            )
            logger.debug(f"OpenCV detected {len(faces)} faces")

            for x, y, w, h in faces:
                face_area = w * h
                image_area = image.shape[0] * image.shape[1]
                area_ratio = face_area / image_area
                confidence = min(0.6 + (area_ratio * 1.5), 0.9)
                max_confidence = max(max_confidence, confidence)
                faces_info.append(
                    {"bbox": [int(x), int(y), int(w), int(h)], "confidence": confidence, "method": "OpenCV"}
                )

            return len(faces_info), faces_info, max_confidence
        except Exception as e:
            logger.error(f"OpenCV face detection failed: {e}")
            return 0, [], 0.0

    def _detect_hands(self, image: np.ndarray) -> Tuple[int, List[dict], float]:
        """Detect hands using skin-colour segmentation + contour analysis."""
        hands_info = []
        max_confidence = 0.0

        if not self.opencv_available:
            logger.warning("Hand detection not available")
            return 0, [], 0.0

        try:
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

            lower_skin1 = np.array([0, 20, 70], dtype=np.uint8)
            upper_skin1 = np.array([20, 255, 255], dtype=np.uint8)
            lower_skin2 = np.array([0, 10, 60], dtype=np.uint8)
            upper_skin2 = np.array([20, 80, 200], dtype=np.uint8)

            skin_mask = cv2.add(
                cv2.inRange(hsv, lower_skin1, upper_skin1),
                cv2.inRange(hsv, lower_skin2, upper_skin2),
            )

            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_OPEN, kernel)
            skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_CLOSE, kernel)

            contours, _ = cv2.findContours(
                skin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            for contour in contours:
                area = cv2.contourArea(contour)
                if not (500 < area < 15000):
                    continue

                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = float(w) / h
                if not (0.4 < aspect_ratio < 2.5):
                    continue

                confidence = min(area / 5000, 0.8)
                max_confidence = max(max_confidence, confidence)

                hand_region = image[y : y + h, x : x + w]
                gesture_type = self._analyze_opencv_hand_gesture(hand_region, contour)

                relative_y = (y + h // 2) / image.shape[0]
                is_suspicious = relative_y < 0.4 or gesture_type in [
                    "pointing",
                    "phone_holding",
                ]

                hands_info.append(
                    {
                        "bbox": [x, y, w, h],
                        "confidence": confidence,
                        "type": "hand",
                        "suspicious": is_suspicious,
                        "gesture_type": gesture_type,
                        "relative_y": relative_y,
                        "method": "OpenCV_Enhanced",
                    }
                )
                logger.debug(f"Enhanced hand detected: {gesture_type}, suspicious: {is_suspicious}")

                if len(hands_info) >= 2:  # limit to 2 hands for performance
                    break

            return len(hands_info), hands_info, max_confidence

        except Exception as e:
            logger.error(f"Enhanced OpenCV hand detection failed: {e}")
            return 0, [], 0.0

    def _analyze_opencv_hand_gesture(
        self, hand_region: np.ndarray, contour: np.ndarray
    ) -> str:
        """Classify a hand gesture from its contour."""
        try:
            gray = cv2.cvtColor(hand_region, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
            contours, _ = cv2.findContours(
                thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            finger_contours = [
                c for c in contours if 100 < cv2.contourArea(c) < 1000
            ]

            if len(finger_contours) >= 4:
                return "open_hand"
            if len(finger_contours) == 2:
                hull_area = cv2.contourArea(cv2.convexHull(finger_contours[0]))
                cnt_area = cv2.contourArea(finger_contours[0])
                if cnt_area > 0 and (hull_area / cnt_area) < 0.8:
                    return "pointing"

            return "normal"
        except Exception as e:
            logger.debug(f"OpenCV gesture analysis failed: {e}")
            return "unknown"

    def _detect_objects(self, image: np.ndarray) -> List[dict]:
        """
        Detect objects using YOLO. Returns a list of dicts with keys:
        class_name, confidence, bbox, method.
        Falls back to an empty list when YOLO is unavailable.
        """
        if not self.yolo_available or self.yolo_model is None:
            logger.debug("YOLO not available – skipping object detection")
            return []

        try:
            results = self.yolo_model(image, conf=0.3, verbose=False)
            detected: List[dict] = []

            for result in results:
                if result.boxes is None:
                    continue
                for box in result.boxes:
                    class_id = int(box.cls[0])
                    class_name = self.yolo_model.names.get(class_id, str(class_id))
                    confidence = float(box.conf[0])
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    detected.append(
                        {
                            "class_name": class_name,
                            "confidence": confidence,
                            "bbox": [int(x1), int(y1), int(x2 - x1), int(y2 - y1)],
                            "method": "YOLO",
                        }
                    )

            logger.debug(f"YOLO detected {len(detected)} objects")
            return detected

        except Exception as e:
            logger.error(f"YOLO object detection failed: {e}")
            return []

    # ──────────────────────────────────────────────────────────────────────────
    # Main frame analysis
    # ──────────────────────────────────────────────────────────────────────────

    def analyze_frame(self, exam_id: str, student_id: str, image_data: bytes):
        """Analyse a single webcam frame and create any resulting violations."""
        logger.info(f"Analyzing frame for student {student_id}")

        try:
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if img is None:
                logger.error("Failed to decode image")
                return {"message": "Invalid image data"}

            logger.debug(f"Image shape: {img.shape}")
            violations_detected = []

            # ── Face detection ─────────────────────────────────────────────────
            face_count, faces_info, face_confidence = self._detect_faces(img)
            logger.info(f"Face detection: {face_count} faces (confidence: {face_confidence:.2f})")

            if face_count == 0:
                violations_detected.append(
                    self.create_violation(
                        ViolationCreate(
                            exam_id=exam_id,
                            student_id=student_id,
                            type=ViolationType.FACE_NOT_VISIBLE,
                            severity=ViolationSeverity.HIGH,
                            description="No face detected in webcam feed",
                            metadata={"faces_count": 0},
                            confidence_score=1.0,
                            detection_method="OpenCV",
                        )
                    )
                )
            elif face_count > 1:
                violations_detected.append(
                    self.create_violation(
                        ViolationCreate(
                            exam_id=exam_id,
                            student_id=student_id,
                            type=ViolationType.MULTIPLE_FACES,
                            severity=ViolationSeverity.CRITICAL,
                            description=f"Multiple faces detected: {face_count} faces",
                            metadata={"faces_count": face_count, "faces_info": faces_info},
                            confidence_score=face_confidence,
                            detection_method="OpenCV",
                        )
                    )
                )

            # ── Hand detection ─────────────────────────────────────────────────
            hands_count, hands_info, hands_confidence = self._detect_hands(img)
            logger.info(f"Hand detection: {hands_count} hands (confidence: {hands_confidence:.2f})")

            for hand in hands_info:
                if hand.get("suspicious", False) and hand.get("confidence", 0) > 0.5:
                    gesture_type = hand.get("gesture_type", "unknown")
                    severity = (
                        ViolationSeverity.HIGH
                        if gesture_type in ["pointing", "phone_holding"]
                        else ViolationSeverity.MEDIUM
                    )
                    violations_detected.append(
                        self.create_violation(
                            ViolationCreate(
                                exam_id=exam_id,
                                student_id=student_id,
                                type=ViolationType.PALM_DETECTED,
                                severity=severity,
                                description=f"Suspicious hand detected: {gesture_type}",
                                metadata=hand,
                                confidence_score=hand.get("confidence", 0.5),
                                detection_method=hand.get("method", "OpenCV_Enhanced"),
                            )
                        )
                    )
                    logger.warning(f"Hand violation: {gesture_type}")
                    break  # one violation per frame for hand

            # ── Object detection ───────────────────────────────────────────────
            detected_objects = self._detect_objects(img)
            logger.info(f"Object detection: {len(detected_objects)} objects")

            suspicious_objects_count = 0
            termination_threshold = 3

            for obj in detected_objects:
                class_name = obj["class_name"].lower()
                confidence = obj["confidence"]
                logger.debug(f"Object: {class_name} (confidence: {confidence:.2f})")

                if any(t in class_name for t in ["phone", "cell", "mobile"]):
                    if confidence > 0.3:
                        logger.info(f"Phone detected: {class_name} with confidence {confidence:.2f}")
                        # Track high-confidence phone detections
                        phone_tracking_result = self._track_phone_detection(exam_id, student_id, confidence)
                        logger.info(f"Phone tracking result: {phone_tracking_result}")
                        
                        suspicious_objects_count += 1
                        violations_detected.append(
                            self.create_violation(
                                ViolationCreate(
                                    exam_id=exam_id,
                                    student_id=student_id,
                                    type=ViolationType.PHONE_DETECTED,
                                    severity=ViolationSeverity.CRITICAL,
                                    description=f"Phone detected: {class_name} (confidence: {confidence:.2f})",
                                    metadata={
                                        **obj,
                                        "phone_tracking": phone_tracking_result
                                    },
                                    confidence_score=confidence,
                                    detection_method=obj.get("method", "YOLO"),
                                )
                            )
                        )
                        logger.warning(f"PHONE DETECTED: {class_name} (confidence: {confidence:.2f}, tracking_count: {phone_tracking_result.get('count', 0)})")
                        
                        # Check if phone threshold is exceeded and exam should be revoked
                        if phone_tracking_result.get("should_revoke", False):
                            reason = phone_tracking_result.get("revocation_reason", f"Phone detection threshold exceeded: {phone_tracking_result.get('count', 0)} detections")
                            logger.error(f"EXAM REVOKED - PHONE THRESHOLD: {reason}")
                            
                            # Create exam suspension violation
                            suspension_violation = self.create_violation(
                                ViolationCreate(
                                    exam_id=exam_id,
                                    student_id=student_id,
                                    type=ViolationType.EXAM_SUSPENDED,
                                    severity=ViolationSeverity.CRITICAL,
                                    description=f"Exam automatically revoked due to phone violations: {reason}",
                                    metadata={
                                        "revocation_reason": reason,
                                        "phone_detections_count": phone_tracking_result.get("count", 0),
                                        "phone_threshold": phone_tracking_result.get("threshold", 3),
                                        "phone_detections": phone_tracking_result.get("detections", []),
                                        "all_detected_objects": detected_objects,
                                        "revocation_type": "automatic_phone_threshold"
                                    },
                                    confidence_score=1.0,
                                    detection_method="Phone_Threshold_Tracking",
                                )
                            )
                            violations_detected.append(suspension_violation)
                            
                            # Send notification and return immediate termination
                            self._send_exam_revoked_notification(exam_id, student_id, reason, suspension_violation.id)
                            
                            logger.error(f"Returning exam revocation response for student {student_id}")
                            return {
                                "message": "Exam automatically revoked due to excessive phone detections",
                                "violations_detected": len(violations_detected),
                                "violations": [v.dict() for v in violations_detected],
                                "exam_terminated": True,
                                "exam_revoked": True,
                                "termination_reason": reason,
                                "auto_submit": True,
                                "revocation_type": "phone_threshold_exceeded",
                                "phone_tracking": phone_tracking_result
                            }
                        else:
                            logger.info(f"Phone threshold not exceeded yet: count={phone_tracking_result.get('count', 0)}, should_revoke={phone_tracking_result.get('should_revoke', False)}")

                elif class_name in ["laptop", "tablet", "book", "remote", "keyboard"]:
                    if confidence > 0.4:
                        suspicious_objects_count += 1
                        violations_detected.append(
                            self.create_violation(
                                ViolationCreate(
                                    exam_id=exam_id,
                                    student_id=student_id,
                                    type=ViolationType.SUSPICIOUS_OBJECT,
                                    severity=ViolationSeverity.MEDIUM,
                                    description=f"Suspicious object: {class_name} (confidence: {confidence:.2f})",
                                    metadata=obj,
                                    confidence_score=confidence,
                                    detection_method=obj.get("method", "YOLO"),
                                )
                            )
                        )
                        logger.warning(f"SUSPICIOUS OBJECT: {class_name}")

            # ── Termination threshold check ────────────────────────────────────
            if suspicious_objects_count > termination_threshold:
                reason = (
                    f"Exam terminated: {suspicious_objects_count} suspicious objects "
                    f"detected (threshold: {termination_threshold})"
                )
                logger.error(f"OBJECT THRESHOLD EXCEEDED: {reason}")

                violations_detected.append(
                    self.create_violation(
                        ViolationCreate(
                            exam_id=exam_id,
                            student_id=student_id,
                            type=ViolationType.EXAM_SUSPENDED,
                            severity=ViolationSeverity.CRITICAL,
                            description=reason,
                            metadata={
                                "suspicious_objects_count": suspicious_objects_count,
                                "threshold": termination_threshold,
                                "termination_reason": "Object detection threshold exceeded",
                                "detected_objects": [
                                    o for o in detected_objects if o.get("confidence", 0) > 0.3
                                ],
                            },
                            confidence_score=1.0,
                            detection_method="YOLO_Threshold",
                        )
                    )
                )

                return {
                    "message": "Exam terminated due to excessive suspicious objects",
                    "violations_detected": len(violations_detected),
                    "violations": [v.dict() for v in violations_detected],
                    "exam_terminated": True,
                    "termination_reason": reason,
                    "auto_submit": True,
                }

            logger.info(f"Frame analysis complete – {len(violations_detected)} violations detected")

            return {
                "message": "Frame analyzed successfully",
                "violations_detected": len(violations_detected),
                "violations": [v.dict() for v in violations_detected],
                "analysis_results": {
                    "faces": {"count": face_count, "confidence": face_confidence, "details": faces_info},
                    "hands": {"count": hands_count, "confidence": hands_confidence, "details": hands_info},
                    "objects": detected_objects,
                },
                "capabilities": {
                    "opencv": self.opencv_available,
                    "yolo": self.yolo_available,
                    "deepface": self.deepface_available,
                    "mtcnn": False,
                },
                "enhanced_mode": self.enhanced_available,
            }

        except Exception as e:
            logger.error(f"Frame analysis failed: {str(e)}", exc_info=True)
            return {"message": f"Error analyzing frame: {str(e)}"}

    # ──────────────────────────────────────────────────────────────────────────
    # Query helpers
    # ──────────────────────────────────────────────────────────────────────────

    def get_violations_by_exam(self, exam_id: str) -> List[Violation]:
        violations = self._load_violations()
        result = []
        for v in violations.values():
            if v["exam_id"] == exam_id:
                if isinstance(v["timestamp"], str):
                    v["timestamp"] = datetime.fromisoformat(v["timestamp"])
                result.append(Violation(**v))
        return result

    def get_violations_by_student(self, student_id: str) -> List[Violation]:
        violations = self._load_violations()
        result = []
        for v in violations.values():
            if v["student_id"] == student_id:
                if isinstance(v["timestamp"], str):
                    v["timestamp"] = datetime.fromisoformat(v["timestamp"])
                result.append(Violation(**v))
        return result

    def get_violation_count(
        self, exam_id: str, student_id: str, violation_type: ViolationType
    ) -> int:
        violations = self._load_violations()
        return sum(
            1
            for v in violations.values()
            if v["exam_id"] == exam_id
            and v["student_id"] == student_id
            and v["type"] == violation_type.value
        )

    def get_phone_tracking_stats(self, exam_id: str, student_id: str) -> dict:
        """
        Get phone tracking statistics for a specific student in an exam.
        
        Args:
            exam_id: Exam identifier
            student_id: Student identifier
            
        Returns:
            dict: Phone tracking statistics
        """
        phone_tracking = self._load_phone_tracking()
        tracking_key = f"{exam_id}_{student_id}"
        
        if tracking_key not in phone_tracking:
            return {
                "exam_id": exam_id,
                "student_id": student_id,
                "high_confidence_detections": [],
                "detection_count": 0,
                "threshold": 3,
                "threshold_exceeded": False,
                "exam_revoked": False,
                "first_detection": None
            }
        
        tracking_data = phone_tracking[tracking_key]
        detection_count = len(tracking_data.get("high_confidence_detections", []))
        
        return {
            "exam_id": exam_id,
            "student_id": student_id,
            "detection_count": detection_count,
            "threshold": 3,
            "threshold_exceeded": detection_count > 3,
            "exam_revoked": tracking_data.get("exam_revoked", False),
            "first_detection": tracking_data.get("first_detection"),
            "revocation_timestamp": tracking_data.get("revocation_timestamp"),
            "revocation_reason": tracking_data.get("revocation_reason"),
            "high_confidence_detections": tracking_data.get("high_confidence_detections", [])
        }

    def suspend_exam(self, exam_id: str, student_id: str, reason: str = ""):
        """Create a suspension violation and write a notification file."""
        created = self.create_violation(
            ViolationCreate(
                exam_id=exam_id,
                student_id=student_id,
                type=ViolationType.EXAM_SUSPENDED,
                severity=ViolationSeverity.CRITICAL,
                description=f"Exam suspended: {reason}",
                metadata={"reason": reason},
            )
        )

        examiner_id = None
        try:
            from services.exam_service import exam_service

            exam = exam_service.get_exam(exam_id)
            examiner_id = getattr(exam, "created_by", None) if exam else None
        except Exception:
            pass

        notifications_dir = "data/logs"
        os.makedirs(notifications_dir, exist_ok=True)
        notifications_file = os.path.join(notifications_dir, "notifications.json")

        try:
            with open(notifications_file, "r") as f:
                notifications = json.load(f)
        except Exception:
            notifications = []

        notification = {
            "id": str(uuid.uuid4()),
            "exam_id": exam_id,
            "student_id": student_id,
            "examiner_id": examiner_id,
            "type": "exam_suspended",
            "message": f"Exam {exam_id} suspended for student {student_id}: {reason}",
            "violation_id": created.id,
            "timestamp": datetime.now().isoformat(),
        }
        notifications.append(notification)

        try:
            with open(notifications_file, "w") as f:
                json.dump(notifications, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to write notification: {e}")

        logger.warning(
            f"Exam suspended: exam={exam_id}, student={student_id}, examiner={examiner_id}"
        )

        if examiner_id:
            try:
                import asyncio
                from routers.websocket_proctoring import examiner_notification_manager

                asyncio.create_task(
                    examiner_notification_manager.broadcast_notification(
                        exam_id,
                        {
                            "type": "exam_suspended",
                            "exam_id": exam_id,
                            "student_id": student_id,
                            "reason": reason,
                            "violation_id": created.id,
                            "timestamp": datetime.now().isoformat(),
                        },
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to send WebSocket notification: {e}")

        return notification

    def _send_exam_revoked_notification(self, exam_id: str, student_id: str, reason: str, violation_id: str):
        """Send notification when exam is automatically revoked due to phone threshold"""
        examiner_id = None
        try:
            from services.exam_service import exam_service
            exam = exam_service.get_exam(exam_id)
            examiner_id = getattr(exam, "created_by", None) if exam else None
        except Exception:
            pass

        notifications_dir = "data/logs"
        os.makedirs(notifications_dir, exist_ok=True)
        notifications_file = os.path.join(notifications_dir, "notifications.json")

        try:
            with open(notifications_file, "r") as f:
                notifications = json.load(f)
        except Exception:
            notifications = []

        notification = {
            "id": str(uuid.uuid4()),
            "exam_id": exam_id,
            "student_id": student_id,
            "examiner_id": examiner_id,
            "type": "exam_auto_revoked",
            "message": f"Exam {exam_id} automatically revoked for student {student_id}: {reason}",
            "violation_id": violation_id,
            "timestamp": datetime.now().isoformat(),
            "severity": "critical",
            "auto_revocation": True,
            "revocation_reason": reason
        }
        notifications.append(notification)

        try:
            with open(notifications_file, "w") as f:
                json.dump(notifications, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to write auto-revocation notification: {e}")

        logger.warning(f"Exam auto-revoked notification sent: exam={exam_id}, student={student_id}, reason={reason}")

        # Send WebSocket notification if available
        if examiner_id:
            try:
                import asyncio
                from routers.websocket_proctoring import examiner_notification_manager

                asyncio.create_task(
                    examiner_notification_manager.broadcast_notification(
                        exam_id,
                        {
                            "type": "exam_auto_revoked",
                            "exam_id": exam_id,
                            "student_id": student_id,
                            "reason": reason,
                            "violation_id": violation_id,
                            "timestamp": datetime.now().isoformat(),
                            "auto_revocation": True,
                            "severity": "critical"
                        },
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to send WebSocket auto-revocation notification: {e}")

        return notification


# Global service instance
proctoring_service = ProctoringService()