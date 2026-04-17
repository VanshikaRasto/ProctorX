import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useNotification } from '../../context/NotificationContext';
import { studentsAPI, proctoringAPI } from '../../services/api';
import { 
  Camera, 
  Clock, 
  AlertTriangle, 
  Send, 
  Eye,
  Volume2,
  VolumeX,
  Shield,
  Activity
} from 'lucide-react';

const ExamTaking = () => {
  const { examId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { showError, showSuccess, showWarning } = useNotification();

  // Exam state
  const [exam, setExam] = useState(null);
  const [answers, setAnswers] = useState({});
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [timeRemaining, setTimeRemaining] = useState(0);
  const [examStarted, setExamStarted] = useState(false);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  // Enhanced Proctoring state
  const [cameraEnabled, setCameraEnabled] = useState(false);
  const [micEnabled, setMicEnabled] = useState(false);
  const [violations, setViolations] = useState([]);
  const [tabSwitchCount, setTabSwitchCount] = useState(0);
  const [isExamRevoked, setIsExamRevoked] = useState(false);
  const [isExamSuspended, setIsExamSuspended] = useState(false);
  const [suspensionReason, setSuspensionReason] = useState('');
  const [proctoringStatus, setProctoringStatus] = useState('initializing');
  const [lastViolationTime, setLastViolationTime] = useState(null);
  const [aiDetectionActive, setAiDetectionActive] = useState(false);

  // Enhanced monitoring state
  const [faceDetectionCount, setFaceDetectionCount] = useState(0);
  const [handDetectionCount, setHandDetectionCount] = useState(0);
  const [objectDetectionCount, setObjectDetectionCount] = useState(0);

  // Debug state
  const [frameCaptureLogs, setFrameCaptureLogs] = useState([]);

  // Refs
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const timerRef = useRef(null);
  const monitoringIntervalRef = useRef(null);
  const tabSwitchTimeoutRef = useRef(null);
  const visibilityStartTime = useRef(null);

  // Add log to frame capture logs for debugging
  const addFrameLog = (message, type = 'info') => {
    const timestamp = new Date().toLocaleTimeString();
    console.log(`[${timestamp}] ${message}`);
    setFrameCaptureLogs(prev => [...prev.slice(-10), { timestamp, message, type }]);
  };

  const fetchExam = async () => {
    try {
      const examData = await studentsAPI.getExamForTaking(examId);
      setExam(examData);
      setTimeRemaining(examData.duration_minutes * 60);
      
      // Initialize answers
      const initialAnswers = {};
      examData.questions.forEach(q => {
        initialAnswers[q.id] = '';
      });
      setAnswers(initialAnswers);
    } catch (error) {
      showError('Failed to load exam');
      navigate('/student');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchExam();
    return () => {
      // Cleanup resources
      if (timerRef.current) clearInterval(timerRef.current);
      if (monitoringIntervalRef.current) clearInterval(monitoringIntervalRef.current);
      if (tabSwitchTimeoutRef.current) clearTimeout(tabSwitchTimeoutRef.current);
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
    };
  }, [examId]);

  useEffect(() => {
    if (examStarted) {
      setupEnhancedProctoring();
      startTimer();
      setupAdvancedTabDetection();
    }
  }, [examStarted]);

  const setupEnhancedProctoring = async () => {
    setProctoringStatus('setting_up');
    addFrameLog('Setting up enhanced proctoring...', 'info');
    
    try {
      addFrameLog('Requesting camera and microphone access...', 'info');
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { 
          width: { ideal: 640 }, 
          height: { ideal: 480 }, 
          frameRate: { ideal: 15 } 
        }, 
        audio: true 
      });
      
      addFrameLog('Media stream obtained successfully', 'success');
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        addFrameLog('Video element source set', 'info');
        
        // Wait for video metadata to load
        videoRef.current.onloadedmetadata = () => {
          addFrameLog(`Video metadata loaded: ${videoRef.current.videoWidth}x${videoRef.current.videoHeight}`, 'success');
        };
        
        videoRef.current.oncanplay = () => {
          addFrameLog('Video can play', 'success');
        };
      }
      
      streamRef.current = stream;
      setCameraEnabled(true);
      setMicEnabled(true);
      setProctoringStatus('active');
      setAiDetectionActive(true);
      
      showSuccess('AI Proctoring system activated');
      addFrameLog('Proctoring system fully activated', 'success');
      
      // Start enhanced monitoring with AI detection - wait a bit for video to be ready
      setTimeout(() => {
        addFrameLog('Starting frame monitoring interval...', 'info');
        monitoringIntervalRef.current = setInterval(captureAndAnalyzeFrame, 5000); // Every 5 seconds
      }, 2000);
      
    } catch (error) {
      console.error('Proctoring setup failed:', error);
      addFrameLog(`Proctoring setup failed: ${error.message}`, 'error');
      showError('Camera and microphone access required for AI proctoring');
      setProctoringStatus('failed');
      navigate('/student');
    }
  };

  const captureAndAnalyzeFrame = async () => {
    addFrameLog('=== FRAME CAPTURE START ===', 'info');
    
    // Check prerequisites - don't rely on state, check refs directly
    const hasVideoRef = !!videoRef.current;
    const hasStreamRef = !!streamRef.current;
    
    addFrameLog(`Prerequisites: video=${hasVideoRef}, stream=${hasStreamRef}`, 'info');

    if (!hasVideoRef || !hasStreamRef) {
      addFrameLog('EARLY RETURN - missing requirements', 'warning');
      return;
    }

    const video = videoRef.current;
    
    // Check if video is actually ready and playing
    const videoReady = video.readyState >= 2 && video.videoWidth > 0 && video.videoHeight > 0;
    addFrameLog(`Video ready check: ${videoReady} (readyState: ${video.readyState}, dimensions: ${video.videoWidth}x${video.videoHeight})`, 'info');
    
    if (!videoReady) {
      addFrameLog('VIDEO NOT READY - skipping frame capture', 'warning');
      return;
    }

    // Rest of your existing frame capture logic...
    try {
      addFrameLog('Creating canvas for frame capture...', 'info');
      const canvas = document.createElement('canvas');
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      
      const ctx = canvas.getContext('2d');
      if (!ctx) {
        addFrameLog('Failed to get canvas context', 'error');
        return;
      }
      
      addFrameLog('Drawing video frame to canvas...', 'info');
      ctx.drawImage(video, 0, 0);
      
      addFrameLog('Requesting blob from canvas...', 'info');
      
      canvas.toBlob(async (blob) => {
        addFrameLog('BLOB CALLBACK EXECUTED', 'info');
        
        if (!blob) {
          addFrameLog('BLOB IS NULL/UNDEFINED', 'error');
          return;
        }
        
        addFrameLog(`Blob created successfully: ${blob.size} bytes, type: ${blob.type}`, 'success');
        
        try {
          addFrameLog('SENDING TO BACKEND...', 'info');
          const response = await proctoringAPI.submitMonitoringFrame(examId, blob);
          addFrameLog(`BACKEND SUCCESS: ${JSON.stringify(response).substring(0, 100)}...`, 'success');
          
          // CHECK FOR EXAM REVOCATION FIRST - This is critical!
          if (response.exam_revoked || response.exam_terminated) {
            addFrameLog('EXAM REVOKED BY BACKEND!', 'error');
            
            // Set revocation state and show message
            setIsExamRevoked(true);
            const revocationReason = response.termination_reason || 'Excessive phone detections detected';
            setSuspensionReason(revocationReason); // Store the specific reason
            showError(`Exam revoked: ${revocationReason}`);
            
            // Auto-submit exam immediately
            setTimeout(() => {
              handleSubmitExam(true);
            }, 1000);
            
            return; // Stop processing further
          }
          
          // Process violations if exam not revoked
          if (response.violations_detected > 0) {
            addFrameLog(`VIOLATIONS DETECTED: ${response.violations_detected}`, 'warning');
            const newViolations = response.violations;
            setViolations(prev => [...prev, ...newViolations]);
            
            newViolations.forEach(violation => {
              handleAIViolationDetected(violation);
            });
            
            updateDetectionCounts(response.analysis_results);
          } else {
            addFrameLog('No violations detected', 'success');
            updateDetectionCounts(response.analysis_results);
          }
          
          if (response.enhanced_mode) {
            setAiDetectionActive(true);
          }
          
        } catch (error) {
          addFrameLog(`BACKEND ERROR: ${error.message}`, 'error');
          console.error('AI frame analysis failed:', error);
        }
      }, 'image/jpeg', 0.8);
      
    } catch (error) {
      addFrameLog(`CANVAS ERROR: ${error.message}`, 'error');
      console.error('Failed to capture frame:', error);
    }
    
    addFrameLog('=== FRAME CAPTURE END ===', 'info');
  };

  const handleAIViolationDetected = (violation) => {
    const violationType = violation.type;
    const severity = violation.severity;
    const description = violation.description;
    const confidence = violation.confidence_score;
    
    addFrameLog(`AI Violation: ${violationType} (${severity}) - ${confidence}`, 'warning');
    
    // Update detection counts
    switch (violationType) {
      case 'face_not_visible':
      case 'multiple_faces':
      case 'face_looking_away':
        setFaceDetectionCount(prev => prev + 1);
        break;
      case 'palm_detected':
      case 'hand_gestures':
        setHandDetectionCount(prev => prev + 1);
        break;
      case 'phone_detected':
      case 'suspicious_object':
        setObjectDetectionCount(prev => prev + 1);
        
        // Check phone tracking metadata for threshold warnings
        if (violation.metadata && violation.metadata.phone_tracking) {
          const phoneTracking = violation.metadata.phone_tracking;
          const count = phoneTracking.count || 0;
          const threshold = phoneTracking.threshold || 3;
          
          if (count >= 2 && count < threshold) {
            showWarning(`WARNING: ${count} phone detections detected! Exam will be revoked after ${threshold} detections.`);
          }
        }
        break;
    }
    
    // Show appropriate warning based on severity and confidence
    if (severity === 'critical' || (severity === 'high' && confidence > 0.7)) {
      if (violationType === 'phone_detected') {
        showError(`CRITICAL: Phone detected! Confidence: ${Math.round(confidence * 100)}%`);
        handleCriticalViolation(violation);
      } else if (violationType === 'multiple_faces') {
        showError(`CRITICAL: Multiple people detected!`);
        handleCriticalViolation(violation);
      } else {
        showError(`HIGH ALERT: ${description}`);
      }
    } else if (severity === 'high') {
      showWarning(`WARNING: ${description}`);
    } else if (severity === 'medium' && confidence > 0.6) {
      showWarning(`${description}`);
    }
    
    setLastViolationTime(new Date());
  };

  const handleCriticalViolation = (violation) => {
    // For critical violations, give one warning then revoke
    const criticalViolations = violations.filter(v => v.severity === 'critical').length;
    
    if (criticalViolations >= 1) {
      showError('Exam revoked due to critical proctoring violations!');
      setIsExamRevoked(true);
      handleSubmitExam(true);
    }
  };

  const updateDetectionCounts = (analysisResults) => {
    if (analysisResults) {
      addFrameLog(`Analysis results: faces=${analysisResults.faces?.count}, hands=${analysisResults.hands?.count}, objects=${analysisResults.objects?.length}`, 'info');
      
      // Update UI with successful detections (for debugging/info)
      if (analysisResults.faces && analysisResults.faces.count > 0) {
        // Face detected successfully
      }
      if (analysisResults.hands && analysisResults.hands.count > 0) {
        // Hands detected
      }
      if (analysisResults.objects && analysisResults.objects.length > 0) {
        // Objects detected
      }
      
      // Draw bounding boxes on canvas
      drawBoundingBoxes(analysisResults);
    }
  };

  const drawBoundingBoxes = (analysisResults) => {
    const canvas = canvasRef.current;
    const video = videoRef.current;

    if (!canvas || !video) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size to match video
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw face boxes
    if (analysisResults.faces && analysisResults.faces.details) {
      analysisResults.faces.details.forEach((face) => {
        drawBox(ctx, face.bbox, '#22c55e', 2, 'Face', face.confidence); // Green for face
      });
    }

    // Draw hand/palm boxes
    if (analysisResults.hands && analysisResults.hands.details) {
      analysisResults.hands.details.forEach((hand) => {
        const color = hand.suspicious ? '#ef4444' : '#f97316'; // Red if suspicious, orange otherwise
        drawBox(ctx, hand.bbox, color, 2, hand.type || 'Hand', hand.confidence);
      });
    }

    // Draw object boxes
    if (analysisResults.objects && analysisResults.objects.length > 0) {
      analysisResults.objects.forEach((obj) => {
        const isPhone = obj.class_name.toLowerCase().includes('phone') || obj.class_name.toLowerCase().includes('cell') || obj.class_name.toLowerCase().includes('mobile');
        const color = isPhone ? '#dc2626' : '#f59e0b'; // Red for phone, amber for other objects
        const label = isPhone ? '⚠️ PHONE' : obj.class_name;
        drawBox(ctx, obj.bbox, color, 3, label, obj.confidence);
      });
    }
  };

  const drawBox = (ctx, bbox, color, lineWidth, label, confidence = null) => {
    if (!bbox || bbox.length < 4) return;

    const [x, y, w, h] = bbox;

    // Draw rectangle with fill
    ctx.strokeStyle = color;
    ctx.lineWidth = lineWidth;
    ctx.strokeRect(x, y, w, h);

    // Draw semi-transparent fill
    ctx.fillStyle = color + '22'; // Add transparency
    ctx.fillRect(x, y, w, h);

    // Draw label background
    const labelText = confidence ? `${label} ${Math.round(confidence * 100)}%` : label;
    const fontSize = 13;
    ctx.font = `bold ${fontSize}px Arial`;
    
    const textMetrics = ctx.measureText(labelText);
    const textWidth = textMetrics.width + 6;
    const textHeight = fontSize + 4;

    // Draw background for text
    ctx.fillStyle = color;
    ctx.fillRect(x, Math.max(0, y - textHeight - 2), textWidth, textHeight);

    // Draw text
    ctx.fillStyle = '#fff';
    ctx.textBaseline = 'top';
    ctx.fillText(labelText, x + 3, Math.max(2, y - textHeight));
  };

  const setupAdvancedTabDetection = () => {
    let hiddenTime = 0;
    
    const handleVisibilityChange = async () => {
      if (document.hidden) {
        visibilityStartTime.current = Date.now();
        hiddenTime = 0;
        
        // Start counting hidden time
        const hiddenTimer = setInterval(() => {
          hiddenTime += 1;
          if (hiddenTime >= 3) { // If hidden for 3+ seconds
            clearInterval(hiddenTimer);
          }
        }, 1000);
        
        tabSwitchTimeoutRef.current = hiddenTimer;
        
      } else {
        // Tab became visible again
        if (visibilityStartTime.current) {
          const hiddenDuration = Date.now() - visibilityStartTime.current;
          
          if (hiddenDuration > 2000) { // Hidden for more than 2 seconds
            // Use functional state update to get the most recent count
            setTabSwitchCount(prevCount => {
              const newCount = prevCount + 1;
              
              // Report advanced tab switch violation
              const violation = {
                exam_id: examId,
                student_id: user.id,
                type: 'tab_switch',
                severity: newCount === 1 ? 'medium' : newCount === 2 ? 'high' : 'critical',
                description: `Tab switch detected (${Math.round(hiddenDuration/1000)}s hidden, ${newCount} total)`,
                metadata: { 
                  count: newCount,
                  duration_ms: hiddenDuration,
                  timestamp: new Date().toISOString(),
                  threshold_exceeded: newCount > 2,
                  exam_terminated: newCount > 2,
                  termination_reason: newCount > 2 ? `Tab switching limit exceeded (${newCount} switches)` : null
                }
              };
              
              proctoringAPI.reportViolation(violation);

              // If threshold exceeded, terminate the exam
              if (newCount > 2) {
                const reason = `Exam terminated: Tab switching detected (${newCount} times, hidden ${Math.round(hiddenDuration/1000)}s)`;
                setIsExamRevoked(true);
                showError('Exam terminated due to excessive tab switching! Submitting exam automatically...');
                
                // Auto-submit exam with termination flag
                setTimeout(() => {
                  handleSubmitExam(true);
                }, 2000);
              }
              
              if (newCount === 1) {
                showWarning(`WARNING: Tab switching detected (${Math.round(hiddenDuration/1000)}s). This is your first warning.`);
              } else if (newCount === 2) {
                showError('FINAL WARNING: One more tab switch will terminate your exam!');
              } else if (newCount > 2) {
                // Exam terminated: message already shown above
                console.log('Exam terminated due to tab switching');
              }
              
              return newCount; // Return the new count for state update
            });
          }
        }
        
        if (tabSwitchTimeoutRef.current) {
          clearTimeout(tabSwitchTimeoutRef.current);
        }
        visibilityStartTime.current = null;
      }
    };

    // Enhanced focus detection
    const handleFocusLoss = () => {
      if (examStarted && !isExamRevoked) {
        console.log('Window focus lost');
      }
    };

    const handleFocusGain = () => {
      if (examStarted && !isExamRevoked) {
        console.log('Window focus regained');
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('blur', handleFocusLoss);
    window.addEventListener('focus', handleFocusGain);
    
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('blur', handleFocusLoss);
      window.removeEventListener('focus', handleFocusGain);
    };
  };

  const startTimer = () => {
    timerRef.current = setInterval(() => {
      setTimeRemaining(prev => {
        if (prev <= 1) {
          handleSubmitExam(true);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  const startExam = () => {
    setExamStarted(true);
    showSuccess('Exam started with AI Proctoring! Good luck!');
  };

  const handleAnswerChange = (questionId, answer) => {
    setAnswers(prev => ({
      ...prev,
      [questionId]: answer
    }));
  };

  const handleSubmitExam = async (forced = false) => {
    if (!forced && !window.confirm('Are you sure you want to submit your exam?')) {
      return;
    }

    setSubmitting(true);

    try {
      // Build answers array to match backend Answer model
      const examAnswers = exam.questions.map(question => ({
        question_id: question.id.toString(), // Keep as string to match backend
        answer: (answers[question.id] || '').trim()
        // Don't include time_spent_seconds as it's optional and we don't track it
      }));

      // Calculate time taken
      const timeElapsed = (exam.duration_minutes * 60) - timeRemaining;
      const timeTakenMinutes = Math.max(1, Math.ceil(timeElapsed / 60));

      // Convert violations to simple string array as backend expects
      const violationStrings = [];
      
      // Add violation summaries as strings
      violations.forEach(violation => {
        const violationStr = `${violation.type} (${violation.severity}): ${violation.description}`;
        violationStrings.push(violationStr);
      });

      // Add tab switch violations
      if (tabSwitchCount > 0) {
        violationStrings.push(`Tab switching detected ${tabSwitchCount} times`);
      }

      // Add AI detection summaries
      if (faceDetectionCount > 0) {
        violationStrings.push(`Face detection violations: ${faceDetectionCount}`);
      }
      if (handDetectionCount > 0) {
        violationStrings.push(`Hand detection violations: ${handDetectionCount}`);
      }
      if (objectDetectionCount > 0) {
        violationStrings.push(`Object detection violations: ${objectDetectionCount}`);
      }

      // Add exam revocation if applicable
      if (isExamRevoked) {
        violationStrings.push('Exam revoked due to critical proctoring violations');
      }

      // Build submission data matching the original SubmissionCreate model exactly
      const submissionData = {
        exam_id: examId,
        answers: examAnswers,
        time_taken_minutes: timeTakenMinutes,
        violations: violationStrings // Simple string array as expected
      };

      console.log('Submitting exam data (adapted to backend):', submissionData);

      const response = await studentsAPI.submitExam(submissionData);
      
      console.log('Submission response:', response);

      // Cleanup resources
      if (timerRef.current) clearInterval(timerRef.current);
      if (monitoringIntervalRef.current) clearInterval(monitoringIntervalRef.current);
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }

      const message = isExamRevoked 
        ? 'Exam submitted (revoked due to AI-detected violations)' 
        : 'Exam submitted successfully!';
      
      showSuccess(message);
      navigate('/student');
      
    } catch (error) {
      console.error('Submission error:', error);
      
      // Detailed error handling
      if (error.response?.status === 422) {
        console.error('Validation errors:', error.response.data);
        showError(`Validation failed: ${error.response.data.detail || 'Invalid data format'}`);
      } else if (error.response?.status === 400) {
        showError(`Submission failed: ${error.response.data.detail || 'Already submitted or bad request'}`);
      } else {
        showError('Failed to submit exam. Please try again.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const formatTime = (seconds) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  const toggleMic = () => {
    if (streamRef.current) {
      const audioTracks = streamRef.current.getAudioTracks();
      audioTracks.forEach(track => {
        track.enabled = !micEnabled;
      });
      setMicEnabled(!micEnabled);
    }
  };

  const getProctoringStatusColor = () => {
    switch (proctoringStatus) {
      case 'active': return 'text-green-600';
      case 'failed': return 'text-red-600';
      case 'setting_up': return 'text-yellow-600';
      default: return 'text-gray-600';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading enhanced AI proctoring system...</p>
        </div>
      </div>
    );
  }

  if (!examStarted) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="max-w-2xl mx-auto bg-white shadow-lg rounded-lg p-8">
          <div className="text-center">
            <h1 className="text-3xl font-bold text-gray-900 mb-4">{exam.title}</h1>
            <p className="text-gray-600 mb-6">{exam.description}</p>
            
            <div className="grid grid-cols-2 gap-4 mb-8">
              <div className="bg-blue-50 p-4 rounded-lg">
                <Clock className="h-6 w-6 text-blue-600 mx-auto mb-2" />
                <p className="text-sm font-medium text-blue-900">Duration</p>
                <p className="text-lg font-bold text-blue-700">{exam.duration_minutes} minutes</p>
              </div>
              <div className="bg-green-50 p-4 rounded-lg">
                <Eye className="h-6 w-6 text-green-600 mx-auto mb-2" />
                <p className="text-sm font-medium text-green-900">Questions</p>
                <p className="text-lg font-bold text-green-700">{exam.questions.length}</p>
              </div>
            </div>

            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
              <div className="flex">
                <Shield className="h-5 w-5 text-yellow-400" />
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-yellow-800">
                    Enhanced AI Proctoring Notice
                  </h3>
                  <div className="mt-2 text-sm text-yellow-700">
                    <p>This exam uses advanced AI proctoring. Please ensure:</p>
                    <ul className="list-disc list-inside mt-1">
                      <li>Your camera and microphone are enabled</li>
                      <li>You are alone in the room</li>
                      <li>Keep your face visible to the camera</li>
                      <li>Do not use phones, tablets, or other devices</li>
                      <li>Do not switch tabs or leave the exam window</li>
                      <li>Avoid suspicious hand gestures or movements</li>
                    </ul>
                    <p className="mt-2 font-medium">
                      AI will detect: faces, hands, objects, and tab switches
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <button
              onClick={startExam}
              className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-lg transition duration-200 flex items-center mx-auto"
            >
              <Shield className="h-5 w-5 mr-2" />
              Start AI-Proctored Exam
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (isExamRevoked) {
    return (
      <div className="min-h-screen bg-red-50 flex items-center justify-center">
        <div className="max-w-md mx-auto bg-white shadow-lg rounded-lg p-8 text-center">
          <AlertTriangle className="h-16 w-16 text-red-600 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-red-900 mb-4">Exam Revoked by AI</h1>
          <p className="text-red-700 mb-4">
            Your exam has been automatically revoked by the AI proctoring system due to detected violations.
          </p>
          
          {/* Show specific revocation reason if available */}
          {suspensionReason && (
            <div className="bg-red-100 p-3 rounded-lg mb-4">
              <p className="text-sm font-medium text-red-800">
                <strong>Reason:</strong> {suspensionReason}
              </p>
            </div>
          )}
          
          <div className="bg-red-100 p-3 rounded-lg mb-4 text-sm">
            <p><strong>Violations detected:</strong></p>
            <p>• Face violations: {faceDetectionCount}</p>
            <p>• Hand violations: {handDetectionCount}</p>
            <p>• Object violations: {objectDetectionCount}</p>
            <p>• Tab switches: {tabSwitchCount}</p>
          </div>
          <p className="text-red-700 mb-6">
            Your responses have been submitted automatically.
          </p>
          <button
            onClick={() => navigate('/student')}
            className="bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-4 rounded"
          >
            Return to Dashboard
          </button>
        </div>
      </div>
    );
  }

  if (isExamSuspended) {
    return (
      <div className="min-h-screen bg-yellow-50 flex items-center justify-center">
        <div className="max-w-md mx-auto bg-white shadow-lg rounded-lg p-8 text-center">
          <AlertTriangle className="h-16 w-16 text-yellow-600 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-yellow-900 mb-4">Exam Suspended</h1>
          <p className="text-yellow-700 mb-4">
            Your exam has been suspended due to suspicious activity: {suspensionReason}
          </p>
          <p className="text-sm text-gray-500 mb-6">An alert has been sent to the examiner.</p>
          <div className="flex justify-center space-x-3">
            <button
              onClick={async () => {
                // Close exam: submit current answers and return to dashboard
                try {
                  await handleSubmitExam(true);
                } catch (e) {
                  console.error(e);
                }
              }}
              className="bg-yellow-600 hover:bg-yellow-700 text-white font-bold py-2 px-4 rounded"
            >
              Close Exam
            </button>
            <button
              onClick={() => navigate('/student')}
              className="bg-white border border-gray-300 text-gray-700 font-medium py-2 px-4 rounded"
            >
              Return to Dashboard
            </button>
          </div>
        </div>
      </div>
    );
  }

  const currentQ = exam.questions[currentQuestion];

  return (
    <div className="min-h-screen bg-gray-50 exam-container">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div>
              <h1 className="text-xl font-semibold text-gray-900">{exam.title}</h1>
              <p className="text-sm text-gray-500">
                Question {currentQuestion + 1} of {exam.questions.length}
              </p>
            </div>
            
            <div className="flex items-center space-x-4">
              <div className={`flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                timeRemaining <= 300 ? 'bg-red-100 text-red-800' : 'bg-blue-100 text-blue-800'
              }`}>
                <Clock className="h-4 w-4 mr-1" />
                {formatTime(timeRemaining)}
              </div>
              
              {aiDetectionActive && (
                <div className="bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm font-medium">
                  <Activity className="h-4 w-4 mr-1 inline" />
                  AI Active
                </div>
              )}
              
              {tabSwitchCount > 0 && (
                <div className={`px-3 py-1 rounded-full text-sm font-medium ${
                  tabSwitchCount >= 2 ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800'
                }`}>
                  <AlertTriangle className="h-4 w-4 mr-1 inline" />
                  Warnings: {tabSwitchCount}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-3">
            <div className="bg-white shadow rounded-lg p-6">
              <div className="mb-6">
                <h2 className="text-lg font-medium text-gray-900 mb-4">
                  Question {currentQuestion + 1}
                </h2>
                <p className="text-gray-700 text-base leading-relaxed">
                  {currentQ.question}
                </p>
              </div>

              <div className="space-y-4">
                {exam.exam_type === 'mcq' ? (
                  <div className="space-y-3">
                    {currentQ.options?.map((option, index) => (
                      <label key={index} className="flex items-center">
                        <input
                          type="radio"
                          name={`question-${currentQ.id}`}
                          value={option}
                          checked={answers[currentQ.id] === option}
                          onChange={(e) => handleAnswerChange(currentQ.id, e.target.value)}
                          className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300"
                        />
                        <span className="ml-3 text-gray-700">
                          {String.fromCharCode(65 + index)}. {option}
                        </span>
                      </label>
                    ))}
                  </div>
                ) : (
                  <textarea
                    rows={8}
                    value={answers[currentQ.id] || ''}
                    onChange={(e) => handleAnswerChange(currentQ.id, e.target.value)}
                    placeholder="Type your answer here..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  />
                )}
              </div>

              {/* Navigation */}
              <div className="flex justify-between items-center mt-8 pt-6 border-t">
                <button
                  onClick={() => setCurrentQuestion(Math.max(0, currentQuestion - 1))}
                  disabled={currentQuestion === 0}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Previous
                </button>

                <div className="flex space-x-3">
                  {currentQuestion === exam.questions.length - 1 ? (
                    <button
                      onClick={() => handleSubmitExam()}
                      disabled={submitting}
                      className="px-6 py-2 bg-green-600 hover:bg-green-700 text-white font-medium rounded-md disabled:opacity-50"
                    >
                      <Send className="h-4 w-4 mr-2 inline" />
                      {submitting ? 'Submitting...' : 'Submit Exam'}
                    </button>
                  ) : (
                    <button
                      onClick={() => setCurrentQuestion(Math.min(exam.questions.length - 1, currentQuestion + 1))}
                      className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700"
                    >
                      Next
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Enhanced Sidebar */}
          <div className="lg:col-span-1">
            {/* Enhanced Proctoring Panel */}
            <div className="bg-white shadow rounded-lg p-4 mb-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                <Shield className="h-5 w-5 mr-2" />
                AI Proctoring
              </h3>
              
              <div className="space-y-4">
                <div className="relative">
                  <video
                    ref={videoRef}
                    autoPlay
                    muted
                    className="w-full h-32 bg-gray-100 rounded-lg object-cover"
                  />
                  <canvas
                    ref={canvasRef}
                    className="absolute inset-0 w-full h-32 rounded-lg"
                    style={{ position: 'absolute', top: 0, left: 0 }}
                  />
                  <div className="absolute top-2 right-2 flex space-x-1">
                    <button
                      onClick={toggleMic}
                      className={`p-1 rounded-full ${
                        micEnabled ? 'bg-green-600 text-white' : 'bg-red-600 text-white'
                      }`}
                    >
                      {micEnabled ? <Volume2 className="h-3 w-3" /> : <VolumeX className="h-3 w-3" />}
                    </button>
                    <div className={`p-1 rounded-full ${
                      cameraEnabled ? 'bg-green-600 text-white' : 'bg-red-600 text-white'
                    }`}>
                      <Camera className="h-3 w-3" />
                    </div>
                  </div>
                  
                  {/* AI Status Indicator */}
                  <div className="absolute bottom-2 left-2">
                    <div className={`flex items-center text-xs px-2 py-1 rounded ${
                      proctoringStatus === 'active' ? 'bg-green-600 text-white' : 'bg-red-600 text-white'
                    }`}>
                      <Activity className="h-3 w-3 mr-1" />
                      AI
                    </div>
                  </div>
                </div>

                {/* Enhanced Status Information */}
                <div className="text-xs space-y-1">
                  <p className="flex items-center justify-between">
                    <span className="text-gray-600">Camera:</span>
                    <span className={`font-medium ${cameraEnabled ? 'text-green-600' : 'text-red-600'}`}>
                      {cameraEnabled ? 'Active' : 'Inactive'}
                    </span>
                  </p>
                  <p className="flex items-center justify-between">
                    <span className="text-gray-600">Microphone:</span>
                    <span className={`font-medium ${micEnabled ? 'text-green-600' : 'text-red-600'}`}>
                      {micEnabled ? 'Active' : 'Inactive'}
                    </span>
                  </p>
                  <p className="flex items-center justify-between">
                    <span className="text-gray-600">AI Status:</span>
                    <span className={`font-medium ${getProctoringStatusColor()}`}>
                      {proctoringStatus.replace('_', ' ').toUpperCase()}
                    </span>
                  </p>
                </div>

                {/* AI Detection Counters */}
                <div className="border-t pt-3">
                  <p className="text-xs font-medium text-gray-700 mb-2">AI Detection Activity:</p>
                  <div className="grid grid-cols-3 gap-2 text-xs">
                    <div className="text-center">
                      <div className={`w-6 h-6 rounded-full mx-auto mb-1 flex items-center justify-center ${
                        faceDetectionCount > 0 ? 'bg-red-100 text-red-600' : 'bg-gray-100 text-gray-600'
                      }`}>
                        <Eye className="h-3 w-3" />
                      </div>
                      <span className="text-gray-600">Face</span>
                      <div className="font-medium">{faceDetectionCount}</div>
                    </div>
                    <div className="text-center">
                      <div className={`w-6 h-6 rounded-full mx-auto mb-1 flex items-center justify-center ${
                        handDetectionCount > 0 ? 'bg-yellow-100 text-yellow-600' : 'bg-gray-100 text-gray-600'
                      }`}>
                        ✋
                      </div>
                      <span className="text-gray-600">Hand</span>
                      <div className="font-medium">{handDetectionCount}</div>
                    </div>
                    <div className="text-center">
                      <div className={`w-6 h-6 rounded-full mx-auto mb-1 flex items-center justify-center ${
                        objectDetectionCount > 0 ? 'bg-red-100 text-red-600' : 'bg-gray-100 text-gray-600'
                      }`}>
                        📱
                      </div>
                      <span className="text-gray-600">Object</span>
                      <div className="font-medium">{objectDetectionCount}</div>
                    </div>
                  </div>
                </div>

                {/* Last Violation Time */}
                {lastViolationTime && (
                  <div className="border-t pt-3">
                    <p className="text-xs text-gray-600">
                      Last Alert: {lastViolationTime.toLocaleTimeString()}
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Debug Log Panel */}
            {frameCaptureLogs.length > 0 && (
              <div className="bg-white shadow rounded-lg p-4 mb-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">Debug Logs</h3>
                <div className="max-h-40 overflow-y-auto space-y-1 text-xs font-mono">
                  {frameCaptureLogs.slice(-8).map((log, index) => (
                    <div key={index} className={`${
                      log.type === 'error' ? 'text-red-600' :
                      log.type === 'warning' ? 'text-yellow-600' :
                      log.type === 'success' ? 'text-green-600' :
                      'text-gray-600'
                    }`}>
                      <span className="text-gray-400">[{log.timestamp}]</span> {log.message}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Question Navigator */}
            <div className="bg-white shadow rounded-lg p-4">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Questions</h3>
              <div className="grid grid-cols-5 gap-2">
                {exam.questions.map((_, index) => (
                  <button
                    key={index}
                    onClick={() => setCurrentQuestion(index)}
                    className={`w-8 h-8 text-xs font-medium rounded ${
                      index === currentQuestion
                        ? 'bg-blue-600 text-white'
                        : answers[exam.questions[index].id]
                        ? 'bg-green-100 text-green-800'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {index + 1}
                  </button>
                ))}
              </div>
              
              <div className="mt-4 text-xs text-gray-600">
                <div className="flex items-center justify-between">
                  <span>Answered:</span>
                  <span className="font-medium">
                    {Object.values(answers).filter(a => a.trim() !== '').length} / {exam.questions.length}
                  </span>
                </div>
              </div>
            </div>

            {/* Violation Summary */}
            {violations.length > 0 && (
              <div className="bg-white shadow rounded-lg p-4 mt-6">
                <h3 className="text-lg font-medium text-red-900 mb-4 flex items-center">
                  <AlertTriangle className="h-5 w-5 mr-2" />
                  Violations ({violations.length})
                </h3>
                <div className="max-h-32 overflow-y-auto space-y-2">
                  {violations.slice(-3).map((violation, index) => (
                    <div key={index} className={`text-xs p-2 rounded ${
                      violation.severity === 'critical' ? 'bg-red-50 text-red-700' :
                      violation.severity === 'high' ? 'bg-orange-50 text-orange-700' :
                      'bg-yellow-50 text-yellow-700'
                    }`}>
                      <div className="font-medium">{violation.type.replace('_', ' ').toUpperCase()}</div>
                      <div className="truncate">{violation.description}</div>
                      {violation.confidence_score && (
                        <div className="text-xs opacity-75">
                          Confidence: {Math.round(violation.confidence_score * 100)}%
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ExamTaking;