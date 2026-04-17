// src/components/examiner/ExaminerDashboard.js
import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useNotification } from '../../context/NotificationContext';
import { examsAPI, resultsAPI, proctoringAPI, registrationAPI } from '../../services/api';
import { 
  Plus, 
  BookOpen, 
  Users, 
  AlertTriangle, 
  Eye, 
  Upload,
  Settings,
  TrendingUp,
  FileText,
  CheckCircle,
  Clock,
  UserPlus,
  XCircle,
  Send
} from 'lucide-react';

const ExaminerDashboard = () => {
  const [exams, setExams] = useState([]);
  const [selectedExam, setSelectedExam] = useState(null);
  const [results, setResults] = useState([]);
  const [submissions, setSubmissions] = useState([]);
  const [violations, setViolations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [suspensionNotifications, setSuspensionNotifications] = useState([]);
  const [ws, setWs] = useState(null);
  const [expandedStudents, setExpandedStudents] = useState(new Set());
  const [expandedViolationTypes, setExpandedViolationTypes] = useState(new Set());
  const [registrationRequests, setRegistrationRequests] = useState([]);

  const { user } = useAuth();
  const { showError, showSuccess, showWarning } = useNotification();

  // Helper function to get registration requests count
  const getRegistrationRequestsCount = () => {
    return registrationRequests.filter(req => req.status === 'pending').length;
  };

  // Helper function to fetch registration requests
  const fetchRegistrationRequests = async (examId) => {
    try {
      const data = await registrationAPI.getExamRegistrations(examId);
      setRegistrationRequests(data);
    } catch (error) {
      showError('Failed to fetch registration requests');
    }
  };

  // Helper functions for grouping violations
  const groupViolationsByStudent = () => {
    const grouped = {};
    violations.forEach(violation => {
      const studentId = violation.student_id;
      if (!grouped[studentId]) {
        grouped[studentId] = {
          studentId,
          studentName: violation.student_name || `Student ${studentId.substring(0, 8)}...`,
          violations: [],
          violationCounts: {}
        };
      }
      grouped[studentId].violations.push(violation);
      
      // Count by violation type
      const type = violation.type;
      grouped[studentId].violationCounts[type] = (grouped[studentId].violationCounts[type] || 0) + 1;
    });
    return grouped;
  };

  const groupViolationsByType = (studentViolations) => {
    const grouped = {};
    studentViolations.forEach(violation => {
      const type = violation.type;
      if (!grouped[type]) {
        grouped[type] = {
          type,
          typeDisplayName: type.replace('_', ' ').toUpperCase(),
          violations: [],
          severity: violation.severity
        };
      }
      grouped[type].violations.push(violation);
    });
    return grouped;
  };

  const toggleStudentExpansion = (studentId) => {
    const newExpanded = new Set(expandedStudents);
    if (newExpanded.has(studentId)) {
      newExpanded.delete(studentId);
    } else {
      newExpanded.add(studentId);
    }
    setExpandedStudents(newExpanded);
  };

  const toggleViolationTypeExpansion = (key) => {
    const newExpanded = new Set(expandedViolationTypes);
    if (newExpanded.has(key)) {
      newExpanded.delete(key);
    } else {
      newExpanded.add(key);
    }
    setExpandedViolationTypes(newExpanded);
  };

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'critical': return 'text-red-500';
      case 'high': return 'text-orange-500';
      case 'medium': return 'text-yellow-500';
      default: return 'text-blue-500';
    }
  };

  const getSeverityBgColor = (severity) => {
    switch (severity) {
      case 'critical': return 'bg-red-100 text-red-800';
      case 'high': return 'bg-orange-100 text-orange-800';
      case 'medium': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-blue-100 text-blue-800';
    }
  };

  useEffect(() => {
    fetchData();
    setupWebSocketNotifications();

    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, []);

  const setupWebSocketNotifications = () => {
    try {
      const token = localStorage.getItem('token');
      if (!user?.id || !token) return;

      const wsUrl = `ws://localhost:8000/api/v1/proctoring/ws/examiner-notifications/${user.id}?token=${token}`;
      const websocket = new WebSocket(wsUrl);

      websocket.onopen = () => {
        console.log('Connected to examiner notifications');
        // Register for exams
        exams.forEach(exam => {
          websocket.send(JSON.stringify({
            type: 'register_exam',
            exam_id: exam.id
          }));
        });
      };

      websocket.onmessage = (event) => {
        const message = JSON.parse(event.data);
        
        if (message.type === 'exam_suspended') {
          const notification = {
            id: message.violation_id,
            exam_id: message.exam_id,
            student_id: message.student_id,
            reason: message.reason,
            timestamp: message.timestamp
          };
          
          setSuspensionNotifications(prev => [notification, ...prev]);
          showWarning(`⚠️ Exam ${message.exam_id} suspended for student ${message.student_id}: ${message.reason}`);
          
          // Refresh violations
          if (selectedExam?.id === message.exam_id) {
            fetchExamDetails(message.exam_id);
          }
        }
      };

      websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      websocket.onclose = () => {
        console.log('Disconnected from examiner notifications');
        // Optionally attempt to reconnect
        setTimeout(() => {
          setupWebSocketNotifications();
        }, 3000);
      };

      setWs(websocket);
    } catch (error) {
      console.error('Failed to setup WebSocket:', error);
    }
  };

  const fetchData = async () => {
    try {
      setLoading(true);
      const examsData = await examsAPI.getMyExams();
      setExams(examsData);
      
      // Register newly fetched exams with WebSocket
      if (ws && ws.readyState === WebSocket.OPEN) {
        examsData.forEach(exam => {
          ws.send(JSON.stringify({
            type: 'register_exam',
            exam_id: exam.id
          }));
        });
      }
      
      if (examsData.length > 0) {
        setSelectedExam(examsData[0]);
        await fetchExamDetails(examsData[0].id);
      }
    } catch (error) {
      showError('Failed to fetch dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const fetchExamDetails = async (examId) => {
    try {
      const [resultsData, violationsData, submissionsData, registrationData] = await Promise.all([
        resultsAPI.getExamResults(examId).catch(() => []),
        proctoringAPI.getExamViolations(examId).catch(() => []),
        examsAPI.getExamSubmissions(examId).catch(() => []),
        registrationAPI.getExamRegistrations(examId).catch(() => [])
      ]);
      setResults(resultsData);
      setViolations(violationsData);
      setSubmissions(submissionsData);
      setRegistrationRequests(registrationData);
    } catch (error) {
      showError('Failed to fetch exam details');
    }
  };

  const handleExamSelect = async (exam) => {
    setSelectedExam(exam);
    await fetchExamDetails(exam.id);
  };

  const handleActivateExam = async (examId) => {
    try {
      await examsAPI.activateExam(examId);
      showSuccess('Exam activated successfully');
      fetchData();
    } catch (error) {
      showError('Failed to activate exam');
    }
  };
  const handleCompleteExam = async (examId) => {
    try {
      await examsAPI.completeExam(examId);
      showSuccess('Exam completed successfully');
      fetchData();
    } catch (error) {
      showError('Failed to complete exam');
    }
  };
  const handleEvaluateExam = async (examId) => {
    try {
      await resultsAPI.evaluateExam(examId);
      showSuccess('Exam evaluated successfully');
      await fetchExamDetails(examId);
    } catch (error) {
      showError('Failed to evaluate exam');
    }
  };

  const handleDisapproveExam = async (examId) => {
    try {
      await resultsAPI.disapproveExam(examId);
      showSuccess('Exam disapproved - all students given 0 marks');
      await fetchExamDetails(examId);
    } catch (error) {
      showError('Failed to disapprove exam');
    }
  };

  const handleReleaseResult = async (resultId) => {
    try {
      await resultsAPI.releaseResult(resultId);
      showSuccess('Result released to student');
      await fetchExamDetails(selectedExam.id);
    } catch (error) {
      showError('Failed to release result');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Suspension Notifications Banner */}
        {suspensionNotifications.length > 0 && (
          <div className="mb-6 bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded">
            <div className="flex items-start">
              <AlertTriangle className="h-6 w-6 text-yellow-400 mt-0.5" />
              <div className="ml-3 flex-1">
                <h3 className="text-sm font-medium text-yellow-800">
                  Recent Exam Suspensions ({suspensionNotifications.length})
                </h3>
                <div className="mt-2 space-y-2 max-h-48 overflow-y-auto">
                  {suspensionNotifications.map((notification) => (
                    <div key={notification.id} className="text-sm text-yellow-700 bg-yellow-100 p-2 rounded">
                      <p className="font-medium">Exam: {notification.exam_id}</p>
                      <p className="text-xs">Student: {notification.student_id}</p>
                      <p className="text-xs">Reason: {notification.reason}</p>
                      <p className="text-xs text-gray-500">
                        {new Date(notification.timestamp).toLocaleString()}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
              <button
                onClick={() => setSuspensionNotifications([])}
                className="ml-3 text-yellow-400 hover:text-yellow-600"
              >
                ✕
              </button>
            </div>
          </div>
        )}

        {/* Header */}
        <div className="mb-8">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                Examiner Dashboard
              </h1>
              <p className="mt-2 text-gray-600">
                Welcome back, {user?.full_name}
              </p>
            </div>
            <button
              onClick={() => setShowCreateModal(true)}
              className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
            >
              <Plus className="h-4 w-4 mr-2" />
              Create Exam
            </button>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <BookOpen className="h-6 w-6 text-blue-600" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">
                      Total Exams
                    </dt>
                    <dd className="text-lg font-medium text-gray-900">
                      {exams.length}
                    </dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <Users className="h-6 w-6 text-green-600" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">
                      Total Submissions
                    </dt>
                    <dd className="text-lg font-medium text-gray-900">
                      {submissions.length}
                    </dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <AlertTriangle className="h-6 w-6 text-yellow-600" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">
                      Violations
                    </dt>
                    <dd className="text-lg font-medium text-gray-900">
                      {violations.length}
                    </dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <TrendingUp className="h-6 w-6 text-purple-600" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">
                      Avg Score
                    </dt>
                    <dd className="text-lg font-medium text-gray-900">
                      {results.length > 0 
                        ? Math.round(results.reduce((acc, r) => acc + r.percentage, 0) / results.length)
                        : 0}%
                    </dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Exams List */}
          <div className="lg:col-span-1">
            <div className="bg-white shadow rounded-lg">
              <div className="px-6 py-4 border-b border-gray-200">
                <h3 className="text-lg font-medium text-gray-900">My Exams</h3>
              </div>
              <div className="divide-y divide-gray-200 max-h-96 overflow-y-auto">
                {exams.length === 0 ? (
                  <div className="p-6 text-center">
                    <BookOpen className="mx-auto h-12 w-12 text-gray-400" />
                    <h3 className="mt-2 text-sm font-medium text-gray-900">No exams</h3>
                    <p className="mt-1 text-sm text-gray-500">
                      Get started by creating a new exam.
                    </p>
                  </div>
                ) : (
                  exams.map((exam) => (
                    <div
                      key={exam.id}
                      onClick={() => handleExamSelect(exam)}
                      className={`p-4 cursor-pointer hover:bg-gray-50 ${
                        selectedExam?.id === exam.id ? 'bg-blue-50 border-r-2 border-blue-500' : ''
                      }`}
                    >
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <h4 className="text-sm font-medium text-gray-900 truncate">
                            {exam.title}
                          </h4>
                          <p className="mt-1 text-xs text-gray-500">
                            {exam.questions.length} questions • {exam.duration_minutes} min
                          </p>
                        </div>
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          exam.status === 'active' 
                            ? 'bg-green-100 text-green-800'
                            : exam.status === 'draft'
                            ? 'bg-yellow-100 text-yellow-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}>
                          {exam.status}
                        </span>
                      </div>
                      
                      {exam.status === 'draft' && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleActivateExam(exam.id);
                          }}
                          className="mt-2 text-xs text-blue-600 hover:text-blue-800"
                        >
                          Activate Exam
                        </button>
                      )}
                    {exam.status === 'active' && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleCompleteExam(exam.id);
                        }}
                        className="mt-2 inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded text-white bg-gray-600 hover:bg-gray-700"
                      >
                        Complete Exam
                      </button>
                    )}
                  </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Main Content */}
          <div className="lg:col-span-2">
            {selectedExam ? (
              <div className="bg-white shadow rounded-lg">
                <div className="px-6 py-4 border-b border-gray-200">
                  <div className="flex justify-between items-center">
                    <h3 className="text-lg font-medium text-gray-900">
                      {selectedExam.title}
                    </h3>
                    <div className="flex space-x-2">
                      <button
                        onClick={() => handleEvaluateExam(selectedExam.id)}
                        className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded text-white bg-green-600 hover:bg-green-700"
                      >
                        <CheckCircle className="h-3 w-3 mr-1" />
                        Evaluate
                      </button>
                      <button
                        onClick={() => handleDisapproveExam(selectedExam.id)}
                        className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded text-white bg-red-600 hover:bg-red-700"
                      >
                        <XCircle className="h-3 w-3 mr-1" />
                        Disapprove (Give 0)
                      </button>
                    </div>
                  </div>
                </div>

                {/* Tabs */}
                <div className="border-b border-gray-200">
                  <nav className="-mb-px flex space-x-8 px-6">
                    <button
                      onClick={() => setActiveTab('overview')}
                      className={`py-2 px-1 border-b-2 font-medium text-sm ${
                        activeTab === 'overview'
                          ? 'border-blue-500 text-blue-600'
                          : 'border-transparent text-gray-500 hover:text-gray-700'
                      }`}
                    >
                      Overview
                    </button>
                    <button
                      onClick={() => setActiveTab('submissions')}
                      className={`py-2 px-1 border-b-2 font-medium text-sm ${
                        activeTab === 'submissions'
                          ? 'border-blue-500 text-blue-600'
                          : 'border-transparent text-gray-500 hover:text-gray-700'
                      }`}
                    >
                      Submissions ({submissions.length})
                    </button>
                    <button
                      onClick={() => setActiveTab('results')}
                      className={`py-2 px-1 border-b-2 font-medium text-sm ${
                        activeTab === 'results'
                          ? 'border-blue-500 text-blue-600'
                          : 'border-transparent text-gray-500 hover:text-gray-700'
                      }`}
                    >
                      Results ({results.length})
                    </button>
                    <button
                      onClick={() => setActiveTab('violations')}
                      className={`py-2 px-1 border-b-2 font-medium text-sm ${
                        activeTab === 'violations'
                          ? 'border-blue-500 text-blue-600'
                          : 'border-transparent text-gray-500 hover:text-gray-700'
                      }`}
                    >
                      Violations ({violations.length})
                    </button>
                    <button
                      onClick={() => setActiveTab('registrations')}
                      className={`py-2 px-1 border-b-2 font-medium text-sm ${
                        activeTab === 'registrations'
                          ? 'border-blue-500 text-blue-600'
                          : 'border-transparent text-gray-500 hover:text-gray-700'
                      }`}
                    >
                      Registration Requests
                    </button>
                  </nav>
                </div>

                <div className="p-6">
                  {activeTab === 'overview' && (
                    <div className="space-y-6">
                      <div>
                        <h4 className="text-sm font-medium text-gray-900 mb-2">Description</h4>
                        <p className="text-sm text-gray-600">{selectedExam.description}</p>
                      </div>
                      
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <h4 className="text-sm font-medium text-gray-900 mb-2">Exam Details</h4>
                          <dl className="space-y-1 text-sm">
                            <div className="flex justify-between">
                              <dt className="text-gray-500">Type:</dt>
                              <dd className="text-gray-900">{selectedExam.exam_type.toUpperCase()}</dd>
                            </div>
                            <div className="flex justify-between">
                              <dt className="text-gray-500">Duration:</dt>
                              <dd className="text-gray-900">{selectedExam.duration_minutes} minutes</dd>
                            </div>
                            <div className="flex justify-between">
                              <dt className="text-gray-500">Questions:</dt>
                              <dd className="text-gray-900">{selectedExam.questions.length}</dd>
                            </div>
                            <div className="flex justify-between">
                              <dt className="text-gray-500">Total Points:</dt>
                              <dd className="text-gray-900">{selectedExam.total_points}</dd>
                            </div>
                          </dl>
                        </div>
                        
                        <div>
                          <h4 className="text-sm font-medium text-gray-900 mb-2">Student Assignment</h4>
                          <dl className="space-y-1 text-sm">
                            <div className="flex justify-between">
                              <dt className="text-gray-500">Assigned:</dt>
                              <dd className="text-gray-900">{selectedExam.assigned_students?.length || 0}</dd>
                            </div>
                            <div className="flex justify-between">
                              <dt className="text-gray-500">Approved:</dt>
                              <dd className="text-gray-900">{selectedExam.approved_students?.length || 0}</dd>
                            </div>
                            <div className="flex justify-between">
                              <dt className="text-gray-500">Submitted:</dt>
                              <dd className="text-gray-900">{submissions.length}</dd>
                            </div>
                          </dl>
                        </div>
                      </div>
                    </div>
                  )}

                  {activeTab === 'submissions' && (
                    <div>
                      {submissions.length === 0 ? (
                        <div className="text-center py-12">
                          <FileText className="mx-auto h-12 w-12 text-gray-400" />
                          <h3 className="mt-2 text-sm font-medium text-gray-900">No submissions yet</h3>
                          <p className="mt-1 text-sm text-gray-500">
                            Submissions will appear here after students submit their exams.
                          </p>
                        </div>
                      ) : (
                        <div className="space-y-4">
                          {submissions.map((submission) => (
                            <div key={submission.id} className="border border-gray-200 rounded-lg p-6 bg-white shadow-sm">
                              {/* Student Name Header */}
                              <div className="mb-4 pb-3 border-b border-gray-100">
                                <h4 className="text-lg font-semibold text-gray-900">
                                  Student Submission
                                </h4>
                                <div className="mt-2">
                                  <span className="text-base font-medium text-gray-800">
                                    Student Name: {submission.student_name || `Student ${submission.student_id.substring(0, 8)}...`}
                                  </span>
                                </div>
                                <div className="mt-1 text-sm text-gray-600">
                                  Student ID: {submission.student_id}
                                </div>
                              </div>
                              
                              {/* Submission Details Grid */}
                              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <div className="bg-blue-50 p-3 rounded-lg">
                                  <div className="text-sm font-medium text-blue-900">Answers</div>
                                  <div className="text-lg font-bold text-blue-700">
                                    {submission.answers ? submission.answers.length : 0} questions answered
                                  </div>
                                </div>
                                
                                <div className="bg-green-50 p-3 rounded-lg">
                                  <div className="text-sm font-medium text-green-900">Time Taken</div>
                                  <div className="text-lg font-bold text-green-700">
                                    {submission.time_taken_minutes || 0} minutes
                                  </div>
                                </div>
                                
                                <div className="bg-purple-50 p-3 rounded-lg">
                                  <div className="text-sm font-medium text-purple-900">Submitted</div>
                                  <div className="text-sm font-medium text-purple-700">
                                    {new Date(submission.submitted_at).toLocaleString()}
                                  </div>
                                </div>
                              </div>
                              
                              {/* Violations Alert */}
                              {submission.violations && submission.violations.length > 0 && (
                                <div className="mt-4">
                                  <span className="inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium bg-red-100 text-red-800">
                                    <AlertTriangle className="h-4 w-4 mr-2" />
                                    {submission.violations.length} violations during exam
                                  </span>
                                </div>
                              )}
                              
                              {/* Status Badge */}
                              <div className="mt-4 flex justify-end">
                                <span className={`inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium ${
                                  submission.status === 'submitted' 
                                    ? 'bg-blue-100 text-blue-800'
                                    : submission.status === 'graded'
                                    ? 'bg-green-100 text-green-800'
                                    : 'bg-red-100 text-red-800'
                                }`}>
                                  {submission.status}
                                </span>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {activeTab === 'results' && (
                    <div>
                      {results.length === 0 ? (
                        <div className="text-center py-12">
                          <FileText className="mx-auto h-12 w-12 text-gray-400" />
                          <h3 className="mt-2 text-sm font-medium text-gray-900">No results yet</h3>
                          <p className="mt-1 text-sm text-gray-500">
                            Results will appear here after submissions are evaluated.
                          </p>
                        </div>
                      ) : (
                        <div className="space-y-4">
                          {results.map((result) => (
                            <div key={result.id} className="border border-gray-200 rounded-lg p-4">
                              <div className="flex justify-between items-start">
                                <div className="flex-1">
                                  <h5 className="text-sm font-medium text-gray-900">
                                    Student Result
                                  </h5>
                                  <div className="mt-1 text-sm text-gray-500">
                                    Score: {result.total_score}/{result.max_score} ({result.percentage.toFixed(1)}%)
                                  </div>
                                  <div className="mt-1 text-xs text-gray-400">
                                    Evaluated: {new Date(result.evaluated_at).toLocaleString()}
                                  </div>
                                </div>
                                
                                <div className="flex items-center space-x-2">
                                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                                    result.percentage >= 80 
                                      ? 'bg-green-100 text-green-800'
                                      : result.percentage >= 60
                                      ? 'bg-yellow-100 text-yellow-800'
                                      : 'bg-red-100 text-red-800'
                                  }`}>
                                    {result.percentage.toFixed(1)}%
                                  </span>
                                  
                                  {!result.released && (
                                    <button
                                      onClick={() => handleReleaseResult(result.id)}
                                      className="inline-flex items-center px-2 py-1 border border-transparent text-xs font-medium rounded text-white bg-blue-600 hover:bg-blue-700"
                                    >
                                      Release
                                    </button>
                                  )}
                                  
                                  {result.released && (
                                    <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-800">
                                      <CheckCircle className="h-3 w-3 mr-1" />
                                      Released
                                    </span>
                                  )}
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {activeTab === 'violations' && (
                    <div>
                      {violations.length === 0 ? (
                        <div className="text-center py-12">
                          <CheckCircle className="mx-auto h-12 w-12 text-green-400" />
                          <h3 className="mt-2 text-sm font-medium text-gray-900">No violations</h3>
                          <p className="mt-1 text-sm text-gray-500">
                            All students followed the exam guidelines properly.
                          </p>
                        </div>
                      ) : (
                        <div className="space-y-4">
                          {Object.entries(groupViolationsByStudent()).map(([studentId, studentData]) => (
                            <div key={studentId} className="border border-gray-200 rounded-lg overflow-hidden">
                              {/* Student Header */}
                              <div 
                                className="p-4 bg-gray-50 cursor-pointer hover:bg-gray-100 transition-colors"
                                onClick={() => toggleStudentExpansion(studentId)}
                              >
                                <div className="flex items-center justify-between">
                                  <div className="flex items-center space-x-3">
                                    <Users className="h-5 w-5 text-gray-500" />
                                    <div>
                                      <h4 className="font-medium text-gray-900">{studentData.studentName}</h4>
                                      <p className="text-sm text-gray-500">ID: {studentId}</p>
                                    </div>
                                  </div>
                                  
                                  <div className="flex items-center space-x-4">
                                    {/* Violation type badges */}
                                    <div className="flex flex-wrap gap-1">
                                      {Object.entries(studentData.violationCounts).map(([type, count]) => (
                                        <span key={type} className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-gray-100 text-gray-700">
                                          {type.replace('_', ' ')}: {count}
                                        </span>
                                      ))}
                                    </div>
                                    
                                    {/* Expand/Collapse icon */}
                                    <div className="flex items-center text-gray-400">
                                      {expandedStudents.has(studentId) ? (
                                        <span className="text-xs">▼</span>
                                      ) : (
                                        <span className="text-xs">▶</span>
                                      )}
                                    </div>
                                  </div>
                                </div>
                                
                                {/* Summary stats */}
                                <div className="mt-3 flex items-center space-x-6 text-sm text-gray-600">
                                  <span>Total violations: {studentData.violations.length}</span>
                                  <span>Types: {Object.keys(studentData.violationCounts).length}</span>
                                </div>
                              </div>
                              
                              {/* Expanded Student Details */}
                              {expandedStudents.has(studentId) && (
                                <div className="border-t border-gray-200">
                                  {Object.entries(groupViolationsByType(studentData.violations)).map(([type, typeData]) => {
                                    const typeKey = `${studentId}_${type}`;
                                    return (
                                      <div key={type} className="border-b border-gray-100 last:border-b-0">
                                        {/* Violation Type Header */}
                                        <div 
                                          className="p-3 bg-gray-50 cursor-pointer hover:bg-gray-100 transition-colors"
                                          onClick={() => toggleViolationTypeExpansion(typeKey)}
                                        >
                                          <div className="flex items-center justify-between">
                                            <div className="flex items-center space-x-2">
                                              <AlertTriangle className={`h-4 w-4 ${getSeverityColor(typeData.severity)}`} />
                                              <span className="font-medium text-gray-900">{typeData.typeDisplayName}</span>
                                              <span className="text-sm text-gray-500">({typeData.violations.length} instances)</span>
                                            </div>
                                            
                                            <div className="flex items-center space-x-2">
                                              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${getSeverityBgColor(typeData.severity)}`}>
                                                {typeData.severity}
                                              </span>
                                              <div className="text-gray-400">
                                                {expandedViolationTypes.has(typeKey) ? (
                                                  <span className="text-xs">▼</span>
                                                ) : (
                                                  <span className="text-xs">▶</span>
                                                )}
                                              </div>
                                            </div>
                                          </div>
                                        </div>
                                        
                                        {/* Expanded Violation Details */}
                                        {expandedViolationTypes.has(typeKey) && (
                                          <div className="p-3 space-y-2">
                                            {typeData.violations.map((violation, index) => (
                                              <div key={violation.id} className="bg-white border border-gray-100 rounded p-3">
                                                <div className="flex justify-between items-start">
                                                  <div className="flex-1">
                                                    <div className="flex items-center space-x-2 mb-1">
                                                      <span className="text-xs text-gray-500">#{index + 1}</span>
                                                      <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium ${getSeverityBgColor(violation.severity)}`}>
                                                        {violation.severity}
                                                      </span>
                                                    </div>
                                                    <p className="text-sm text-gray-700">{violation.description}</p>
                                                    {violation.type === 'exam_suspended' && (
                                                      <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded">
                                                        <div className="text-sm font-medium text-red-800">
                                                          Revocation Reason:
                                                        </div>
                                                        <div className="text-sm text-red-700">
                                                          {violation.metadata?.revocation_reason || 'No reason provided'}
                                                        </div>
                                                      </div>
                                                    )}
                                                    {violation.metadata && violation.metadata.revocation_reason && violation.type !== 'exam_suspended' && (
                                                      <div className="mt-2 p-2 bg-orange-50 border border-orange-200 rounded">
                                                        <div className="text-sm font-medium text-orange-800">
                                                          Additional Info:
                                                        </div>
                                                        <div className="text-sm text-orange-700">
                                                          {violation.metadata.revocation_reason}
                                                        </div>
                                                      </div>
                                                    )}
                                                    <div className="mt-1 text-xs text-gray-400">
                                                      {new Date(violation.timestamp).toLocaleString()}
                                                    </div>
                                                    {violation.confidence_score && (
                                                      <div className="mt-1 text-xs text-gray-500">
                                                        Confidence: {Math.round(violation.confidence_score * 100)}%
                                                      </div>
                                                    )}
                                                    {violation.detection_method && (
                                                      <div className="mt-1 text-xs text-gray-500">
                                                        Detection: {violation.detection_method}
                                                      </div>
                                                    )}
                                                  </div>
                                                </div>
                                              </div>
                                            ))}
                                          </div>
                                        )}
                                      </div>
                                    );
                                  })}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {activeTab === 'registrations' && (
                    <RegistrationRequestsTab 
                      examId={selectedExam.id} 
                      onUpdate={() => fetchExamDetails(selectedExam.id)}
                    />
                  )}
                </div>
              </div>
            ) : (
              <div className="bg-white shadow rounded-lg p-12 text-center">
                <BookOpen className="mx-auto h-12 w-12 text-gray-400" />
                <h3 className="mt-2 text-sm font-medium text-gray-900">No exam selected</h3>
                <p className="mt-1 text-sm text-gray-500">
                  Select an exam from the list to view details, submissions, results, and violations.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Create Exam Modal */}
      {showCreateModal && (
        <CreateExamModal
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => {
            setShowCreateModal(false);
            fetchData();
          }}
        />
      )}
    </div>
  );
};

// Registration Requests Tab Component
const RegistrationRequestsTab = ({ examId, onUpdate }) => {
  const [registrations, setRegistrations] = useState([]);
  const [loading, setLoading] = useState(true);
  const { showError, showSuccess } = useNotification();

  useEffect(() => {
    fetchRegistrations();
  }, [examId]);

  const fetchRegistrations = async () => {
    try {
      setLoading(true);
      const data = await registrationAPI.getExamRegistrations(examId);
      setRegistrations(data);
    } catch (error) {
      showError('Failed to fetch registration requests');
    } finally {
      setLoading(false);
    }
  };

  const handleStatusUpdate = async (registrationId, status, notes = '') => {
    try {
      await registrationAPI.updateRegistrationStatus(registrationId, status, notes);
      showSuccess(`Registration ${status === 'approved' ? 'approved' : 'rejected'} successfully`);
      fetchRegistrations();
      onUpdate(); // Refresh parent data
    } catch (error) {
      showError(`Failed to ${status} registration`);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div>
      {registrations.length === 0 ? (
        <div className="text-center py-12">
          <UserPlus className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">No registration requests</h3>
          <p className="mt-1 text-sm text-gray-500">
            No students have requested to register for this exam yet.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {registrations.map((registration) => (
            <div key={registration.id} className="border border-gray-200 rounded-lg p-4">
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <h5 className="text-sm font-medium text-gray-900">
                    {registration.student_name}
                  </h5>
                  <p className="text-sm text-gray-600">{registration.student_email}</p>
                  <div className="mt-1 text-xs text-gray-400">
                    Requested: {new Date(registration.requested_at).toLocaleString()}
                  </div>
                  {registration.notes && (
                    <div className="mt-2">
                      <p className="text-sm text-gray-600">
                        <strong>Notes:</strong> {registration.notes}
                      </p>
                    </div>
                  )}
                  {registration.reviewed_at && (
                    <div className="mt-1 text-xs text-gray-400">
                      Reviewed: {new Date(registration.reviewed_at).toLocaleString()}
                    </div>
                  )}
                </div>
                
                <div className="flex items-center space-x-2">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    registration.status === 'approved' 
                      ? 'bg-green-100 text-green-800'
                      : registration.status === 'pending'
                      ? 'bg-yellow-100 text-yellow-800'
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {registration.status}
                  </span>
                  
                  {registration.status === 'pending' && (
                    <div className="flex space-x-2">
                      <button
                        onClick={() => handleStatusUpdate(registration.id, 'approved')}
                        className="inline-flex items-center px-2 py-1 border border-transparent text-xs font-medium rounded text-white bg-green-600 hover:bg-green-700"
                      >
                        <CheckCircle className="h-3 w-3 mr-1" />
                        Approve
                      </button>
                      <button
                        onClick={() => handleStatusUpdate(registration.id, 'rejected')}
                        className="inline-flex items-center px-2 py-1 border border-transparent text-xs font-medium rounded text-white bg-red-600 hover:bg-red-700"
                      >
                        <XCircle className="h-3 w-3 mr-1" />
                        Reject
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// Create Exam Modal Component
const CreateExamModal = ({ onClose, onSuccess }) => {
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    exam_type: 'mcq',
    duration_minutes: 60,
    file_content: '',
    branch: 'CSE'
  });
  const [loading, setLoading] = useState(false);
  const { showError, showSuccess } = useNotification();

  const handleInputChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        setFormData({
          ...formData,
          file_content: e.target.result
        });
      };
      reader.readAsText(file);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      await examsAPI.createExam(formData);
      showSuccess('Exam created successfully!');
      onSuccess();
    } catch (error) {
      showError(error.response?.data?.detail || 'Failed to create exam');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-20 mx-auto p-5 border w-11/12 md:w-3/4 lg:w-1/2 shadow-lg rounded-md bg-white">
        <div className="mt-3">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-medium text-gray-900">Create New Exam</h3>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              <span className="sr-only">Close</span>
              ✕
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Exam Title
              </label>
              <input
                type="text"
                name="title"
                required
                className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                value={formData.title}
                onChange={handleInputChange}
                placeholder="Enter exam title"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                Description
              </label>
              <textarea
                name="description"
                rows={3}
                className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                value={formData.description}
                onChange={handleInputChange}
                placeholder="Enter exam description"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Exam Type
                </label>
                <select
                  name="exam_type"
                  className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  value={formData.exam_type}
                  onChange={handleInputChange}
                >
                  <option value="mcq">Multiple Choice</option>
                  <option value="subjective">Subjective</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Duration (minutes)
                </label>
                <input
                  type="number"
                  name="duration_minutes"
                  min="1"
                  max="300"
                  className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  value={formData.duration_minutes}
                  onChange={handleInputChange}
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                Branch
              </label>
              <select
                name="branch"
                required
                className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                value={formData.branch}
                onChange={handleInputChange}
              >
                <option value="CSE">CSE</option>
                <option value="CS">CS</option>
                <option value="ECE">ECE</option>
                <option value="ME">ME</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                Upload Questions (.txt file)
              </label>
              <div className="mt-1 flex justify-center px-6 pt-5 pb-6 border-2 border-gray-300 border-dashed rounded-md">
                <div className="space-y-1 text-center">
                  <Upload className="mx-auto h-12 w-12 text-gray-400" />
                  <div className="flex text-sm text-gray-600">
                    <label className="relative cursor-pointer bg-white rounded-md font-medium text-blue-600 hover:text-blue-500 focus-within:outline-none focus-within:ring-2 focus-within:ring-offset-2 focus-within:ring-blue-500">
                      <span>Upload a file</span>
                      <input
                        type="file"
                        accept=".txt"
                        className="sr-only"
                        onChange={handleFileUpload}
                        required
                      />
                    </label>
                    <p className="pl-1">or drag and drop</p>
                  </div>
                  <p className="text-xs text-gray-500">
                    TXT files only
                  </p>
                </div>
              </div>
              {formData.file_content && (
                <p className="mt-2 text-sm text-green-600">
                  ✓ File uploaded successfully
                </p>
              )}
            </div>

            <div className="flex justify-end space-x-3 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
              >
                {loading ? 'Creating...' : 'Create Exam'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default ExaminerDashboard;