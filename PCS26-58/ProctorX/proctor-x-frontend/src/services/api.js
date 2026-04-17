// Import axios for HTTP client functionality
import axios from 'axios';

// Base URL for API endpoints - uses environment variable or defaults to localhost
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

// Create axios instance with default configuration
const api = axios.create({
  baseURL: API_BASE_URL,  // Base URL for all API requests
  headers: {
    'Content-Type': 'application/json',  // Default content type for requests
  },
});

// Request interceptor - Automatically add authentication token to all outgoing requests
api.interceptors.request.use(
  (config) => {
    // Get token from localStorage
    const token = localStorage.getItem('token');
    if (token) {
      // Add Bearer token to Authorization header
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)  // Pass through request errors
);

// Response interceptor - Handle authentication errors globally
api.interceptors.response.use(
  (response) => response,  // Pass through successful responses
  (error) => {
    // If we get a 401 Unauthorized response, clear token and redirect to login
    if (error.response?.status === 401) {
      localStorage.removeItem('token');  // Clear invalid token
      window.location.href = '/login';   // Redirect to login page
    }
    return Promise.reject(error);  // Pass through other errors
  }
);

// Authentication API - handles user login, registration, and token management
export const authAPI = {
  // Login user with credentials
  login: async (credentials) => {
    const response = await api.post('/auth/login', credentials);
    return response.data;
  },

  // Register new user account
  register: async (userData) => {
    const response = await api.post('/auth/register', userData);
    return response.data;
  },

  // Get current authenticated user information
  getCurrentUser: async () => {
    const response = await api.get('/auth/me');
    return response.data;
  },

  // Logout user and clear authentication
  logout: async () => {
    await api.post('/auth/logout');
    localStorage.removeItem('token');  // Clear stored token
  },

  // Verify if current token is still valid
  verifyToken: async () => {
    const response = await api.post('/auth/verify-token');
    return response.data;
  },
};

// Exams API - handles exam creation, management, and operations for examiners
export const examsAPI = {
  // Create a new exam
  createExam: async (examData) => {
    const response = await api.post('/exams/', examData);
    return response.data;
  },

  // Get all exams created by the current examiner
  getMyExams: async () => {
    const response = await api.get('/exams/my-exams');
    return response.data;
  },

  // Get specific exam details by ID
  getExam: async (examId) => {
    const response = await api.get(`/exams/${examId}`);
    return response.data;
  },

  // Assign exam to specific students
  assignExam: async (examId, studentIds) => {
    const response = await api.post(`/exams/${examId}/assign`, {
      exam_id: examId,
      student_ids: studentIds,
    });
    return response.data;
  },

  // Approve a student's registration for an exam
  approveStudent: async (examId, studentId) => {
    const response = await api.post(`/exams/${examId}/approve/${studentId}`);
    return response.data;
  },

  // Activate an exam (make it available for students to take)
  activateExam: async (examId) => {
    const response = await api.post(`/exams/${examId}/activate`);
    return response.data;
  },

  // Complete an exam (end the exam period)
  completeExam: async (examId) => {
    const response = await api.post(`/exams/${examId}/complete`);
    return response.data;
  },
  
  // Get all submissions for a specific exam
  getExamSubmissions: async (examId) => {
    const response = await api.get(`/exams/${examId}/submissions`);
    return response.data;
  },
};

// Students API - handles exam operations for students
export const studentsAPI = {
  // Get all exams assigned to the current student
  getAssignedExams: async () => {
    const response = await api.get('/students/my-exams');
    return response.data;
  },

  // Get exam details for taking an exam
  getExamForTaking: async (examId) => {
    const response = await api.get(`/students/exam/${examId}`);
    return response.data;
  },

  // Submit completed exam answers
  submitExam: async (submissionData) => {
    const response = await api.post('/students/submit', submissionData);
    return response.data;
  },

  // Get all submissions made by the current student
  getMySubmissions: async () => {
    const response = await api.get('/students/submissions');
    return response.data;
  },
};

// Results API - handles exam results and grading operations
export const resultsAPI = {
  // Get results for the current user (student or examiner)
  getMyResults: async () => {
    const response = await api.get('/results/my-results');
    return response.data;
  },

  // Get results for a specific exam (for examiners)
  getExamResults: async (examId) => {
    const response = await api.get(`/results/exam/${examId}`);
    return response.data;
  },

  // Release a result to make it visible to students
  releaseResult: async (resultId) => {
    const response = await api.post(`/results/${resultId}/release`);
    return response.data;
  },

  // Evaluate and grade all submissions for an exam
  evaluateExam: async (examId) => {
    const response = await api.post(`/results/exam/${examId}/evaluate`);
    return response.data;
  },

  // Disapprove exam and give 0 marks to all students
  disapproveExam: async (examId) => {
    const response = await api.post(`/results/exam/${examId}/disapprove`);
    return response.data;
  },
};

// Enhanced AI Proctoring API - handles AI-powered monitoring and violation detection
export const proctoringAPI = {
  // Legacy endpoints (keep for backward compatibility)
  
  // Report a manual violation by examiner
  reportViolation: async (violationData) => {
    const response = await api.post('/proctoring/violations', violationData);
    return response.data;
  },

  // Suspend a student's exam due to violations
  suspendExam: async (examId, studentId, reason = '') => {
    const response = await api.post('/proctoring/suspend', null, {
      params: {
        exam_id: examId,
        student_id: studentId,
        reason: reason
      }
    });
    return response.data;
  },

  // Get all violations for a specific exam
  getExamViolations: async (examId) => {
    const response = await api.get(`/proctoring/violations/exam/${examId}`);
    return response.data;
  },

  // Get all violations for a specific student
  getStudentViolations: async (studentId) => {
    const response = await api.get(`/proctoring/violations/student/${studentId}`);
    return response.data;
  },

  // Enhanced AI frame analysis endpoint - analyzes video frames for violations
  submitMonitoringFrame: async (examId, imageBlob) => {
    console.log('Submitting frame for exam:', examId);
    console.log('Image blob size:', imageBlob?.size);
    
    // Create FormData for file upload
    const formData = new FormData();
    formData.append('image', imageBlob, 'frame.jpg');
    
    try {
      const response = await api.post('/proctoring/monitor-frame', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        params: { 
          exam_id: examId 
        },
        timeout: 10000, // 10 second timeout for frame analysis
      });
      
      console.log('Backend response:', response.data);
      return response.data;
    } catch (error) {
      console.error('Frame submission failed:', error.response?.data || error.message);
      
      // Don't throw error for individual frame failures to avoid interrupting exam
      return {
        message: 'Frame analysis failed',
        violations_detected: 0,
        violations: [],
        error: error.message
      };
    }
  },

  // Enhanced AI proctoring endpoints (v1 API)
  
  // Analyze a single frame using enhanced AI detection
  analyzeFrame: async (examId, imageBlob) => {
    const formData = new FormData();
    formData.append('image', imageBlob, 'frame.jpg');
    
    const response = await api.post('/v1/proctoring/analyze-frame', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      params: { 
        exam_id: examId 
      },
    });
    return response.data;
  },

  // Get AI proctoring system health and capabilities
  getAIHealth: async () => {
    try {
      const response = await api.get('/ai-health');
      return response.data;
    } catch (error) {
      return {
        status: 'unavailable',
        message: 'AI health check failed'
      };
    }
  },

  // Test AI detection capabilities with sample data
  testAIDetection: async () => {
    try {
      const response = await api.get('/test-ai-detection');
      return response.data;
    } catch (error) {
      return {
        status: 'error',
        message: 'AI detection test failed'
      };
    }
  },

  // Get proctoring statistics for a specific exam
  getProctoringStats: async (examId) => {
    const response = await api.get(`/v1/proctoring/stats/${examId}`);
    return response.data;
  },

  // Get violation counts with optional filtering by type
  getViolationCount: async (examId, studentId, violationType = null) => {
    const params = violationType ? `?violation_type=${violationType}` : '';
    const response = await api.get(`/v1/proctoring/violations/count/${examId}/${studentId}${params}`);
    return response.data;
  },

  // Get phone tracking statistics for high-confidence phone detections
  getPhoneTrackingStats: async (examId, studentId) => {
    const response = await api.get(`/proctoring/phone-tracking/${examId}/${studentId}`);
    return response.data;
  },

  // Get WebSocket token for real-time monitoring
  getWebSocketToken: async () => {
    return localStorage.getItem('token');
  },

  // Send real-time alert to a specific student
  sendAlertToStudent: async (studentId, alertMessage) => {
    const response = await api.post(`/v1/proctoring/ws/send-alert/${studentId}`, alertMessage);
    return response.data;
  },
};

// Registration API - handles exam registration and approval workflows
export const registrationAPI = {
  // Get all available exams that a student can register for
  getAvailableExams: async () => {
    const response = await api.get('/registrations/available-exams');
    return response.data;
  },

  // Register a student for a specific exam
  registerForExam: async (examId, notes = '') => {
    const response = await api.post('/registrations/register', {
      exam_id: examId,
      notes: notes,
    });
    return response.data;
  },

  // Get all registrations for the current user
  getMyRegistrations: async () => {
    const response = await api.get('/registrations/my-registrations');
    return response.data;
  },

  // Get all registrations for a specific exam (for examiners)
  getExamRegistrations: async (examId) => {
    const response = await api.get(`/registrations/exam/${examId}/registrations`);
    return response.data;
  },

  // Update the status of a registration (approve/reject)
  updateRegistrationStatus: async (registrationId, status, notes = '') => {
    const response = await api.put(`/registrations/registrations/${registrationId}`, {
      status: status,
      notes: notes,
    });
    return response.data;
  },
};

// Enhanced Monitoring API - handles system monitoring and health checks
export const monitoringAPI = {
  // Basic health check endpoint
  getHealthCheck: async () => {
    const response = await api.get('/monitoring/healthz');
    return response.data;
  },

  // Get system metrics and performance data
  getMetrics: async () => {
    const response = await api.get('/monitoring/metrics');
    return response.data;
  },

  // Get application logs
  getLogs: async () => {
    const response = await api.get('/monitoring/logs');
    return response.data;
  },

  // Get general system statistics
  getStats: async () => {
    const response = await api.get('/monitoring/stats');
    return response.data;
  },

  // AI-specific monitoring endpoints
  
  // Get detailed system status including AI capabilities
  getSystemStatus: async () => {
    const response = await api.get('/system/status');
    return response.data;
  },

  // Get WebSocket connection status for real-time monitoring
  getWebSocketStatus: async () => {
    const response = await api.get('/websocket-status');
    return response.data;
  },
};

// Utility functions for proctoring operations
export const proctoringUtils = {
  // Create a WebSocket connection for real-time monitoring
  createWebSocket: (examId, token) => {
    const wsUrl = `ws://localhost:8000/api/v1/proctoring/ws/proctoring/${examId}?token=${token}`;
    return new WebSocket(wsUrl);
  },

  // Convert blob to base64 string (alternative submission method)
  blobToBase64: (blob) => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  },

  // Validate image blob before submission
  validateImage: (blob) => {
    return blob && 
           blob.type && 
           blob.type.startsWith('image/') && 
           blob.size > 0 && 
           blob.size < 5 * 1024 * 1024; // Less than 5MB
  },

  // Create optimized image blob from canvas with specified quality
  createOptimizedBlob: (canvas, quality = 0.8) => {
    return new Promise((resolve) => {
      canvas.toBlob((blob) => {
        resolve(blob);
      }, 'image/jpeg', quality);
    });
  },
};

// Export the default axios instance for direct usage if needed
export default api;