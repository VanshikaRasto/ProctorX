import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useNotification } from '../../context/NotificationContext';
import { studentsAPI, resultsAPI, registrationAPI } from '../../services/api';
import { 
  BookOpen, 
  Clock, 
  CheckCircle, 
  XCircle, 
  AlertTriangle, 
  Calendar,
  Trophy,
  Play,
  Search,
  UserPlus,
  Send
} from 'lucide-react';

const StudentDashboard = () => {
  const [exams, setExams] = useState([]);
  const [results, setResults] = useState([]);
  const [availableExams, setAvailableExams] = useState([]);
  const [registrations, setRegistrations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('exams');
  const [showRegisterModal, setShowRegisterModal] = useState(false);
  const [selectedExam, setSelectedExam] = useState(null);
  
  const { user } = useAuth();
  const { showError, showSuccess } = useNotification();
  const navigate = useNavigate();

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      console.log('Starting data fetch...');
      
      const [examsData, resultsData, availableExamsData, registrationsData] = await Promise.all([
        studentsAPI.getAssignedExams().catch(err => {
          console.error('Assigned exams error:', err);
          return [];
        }),
        resultsAPI.getMyResults().catch(err => {
          console.error('Results error:', err);
          return [];
        }),
        registrationAPI.getAvailableExams().catch(err => {
          console.error('Available exams error:', err);
          return [];
        }),
        registrationAPI.getMyRegistrations().catch(err => {
          console.error('Registrations error:', err);
          return [];
        })
      ]);
      
      console.log('=== FETCH DATA RESULTS ===');
      console.log('Assigned exams:', examsData);
      console.log('Results:', resultsData);
      console.log('Available exams:', availableExamsData);
      console.log('Available exams count:', availableExamsData?.length || 0);
      console.log('Registrations:', registrationsData);
      console.log('========================');
      
      setExams(examsData || []);
      setResults(resultsData || []);
      setAvailableExams(availableExamsData || []);
      setRegistrations(registrationsData || []);
      
    } catch (error) {
      console.error('Fetch data error:', error);
      showError('Failed to fetch dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const getExamStatus = (exam) => {
    if (exam.status === 'active') {
      return { status: 'Available', color: 'green', icon: CheckCircle };
    } else if (exam.status === 'draft') {
      return { status: 'Not Ready', color: 'yellow', icon: AlertTriangle };
    } else {
      return { status: 'Completed', color: 'gray', icon: XCircle };
    }
  };

  const getRegistrationStatus = (status) => {
    switch (status) {
      case 'pending':
        return { text: 'Pending', color: 'yellow', icon: Clock };
      case 'approved':
        return { text: 'Approved', color: 'green', icon: CheckCircle };
      case 'rejected':
        return { text: 'Rejected', color: 'red', icon: XCircle };
      default:
        return { text: 'Unknown', color: 'gray', icon: AlertTriangle };
    }
  };

  const startExam = (examId) => {
    navigate(`/student/exam/${examId}`);
  };

  const handleRegisterForExam = (exam) => {
    console.log('Registering for exam:', exam);
    setSelectedExam(exam);
    setShowRegisterModal(true);
  };

  const handleRegisterSubmit = async (notes) => {
    try {
      await registrationAPI.registerForExam(selectedExam.id, notes);
      showSuccess('Registration request submitted successfully!');
      setShowRegisterModal(false);
      setSelectedExam(null);
      fetchData(); // Refresh data
    } catch (error) {
      showError(error.response?.data?.detail || 'Failed to register for exam');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  console.log('=== RENDER STATE ===');
  console.log('Available exams in render:', availableExams);
  console.log('Available exams length:', availableExams?.length || 0);
  console.log('Active tab:', activeTab);
  console.log('==================');

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">
            Welcome, {user?.full_name}
          </h1>
          <p className="mt-2 text-gray-600">
            Manage your exams and view your results
          </p>
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
                      Assigned Exams
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
                  <Search className="h-6 w-6 text-purple-600" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">
                      Available Exams
                    </dt>
                    <dd className="text-lg font-medium text-gray-900">
                      {availableExams.length}
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
                  <Trophy className="h-6 w-6 text-green-600" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">
                      Completed Exams
                    </dt>
                    <dd className="text-lg font-medium text-gray-900">
                      {results.length}
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
                  <Calendar className="h-6 w-6 text-orange-600" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">
                      Average Score
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

        {/* Tabs */}
        <div className="border-b border-gray-200 mb-6">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => setActiveTab('exams')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'exams'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              My Exams
            </button>
            <button
              onClick={() => setActiveTab('available')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'available'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Available Exams ({availableExams.length})
            </button>
            <button
              onClick={() => setActiveTab('registrations')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'registrations'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              My Registrations
            </button>
            <button
              onClick={() => setActiveTab('results')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'results'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Results
            </button>
          </nav>
        </div>

        {/* Content */}
        {activeTab === 'exams' && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {exams.length === 0 ? (
              <div className="col-span-full text-center py-12">
                <BookOpen className="mx-auto h-12 w-12 text-gray-400" />
                <h3 className="mt-2 text-sm font-medium text-gray-900">No exams assigned</h3>
                <p className="mt-1 text-sm text-gray-500">
                  You don't have any exams assigned yet.
                </p>
              </div>
            ) : (
              exams.map((exam) => {
                const statusInfo = getExamStatus(exam);
                const StatusIcon = statusInfo.icon;
                
                return (
                  <div key={exam.id} className="bg-white overflow-hidden shadow rounded-lg">
                    <div className="px-4 py-5 sm:p-6">
                      <div className="flex items-center justify-between mb-4">
                        <h3 className="text-lg font-medium text-gray-900 truncate">
                          {exam.title}
                        </h3>
                        <div className={`flex items-center text-sm text-${statusInfo.color}-600`}>
                          <StatusIcon className="h-4 w-4 mr-1" />
                          {statusInfo.status}
                        </div>
                      </div>
                      
                      <p className="text-sm text-gray-500 mb-4 line-clamp-2">
                        {exam.description}
                      </p>
                      
                      <div className="flex items-center justify-between text-sm text-gray-500 mb-4">
                        <div className="flex items-center">
                          <Clock className="h-4 w-4 mr-1" />
                          {exam.duration_minutes} minutes
                        </div>
                        <div className="flex items-center">
                          <Trophy className="h-4 w-4 mr-1" />
                          {exam.total_points} points
                        </div>
                      </div>
                      
                      <div className="flex items-center justify-between">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          exam.exam_type === 'mcq' 
                            ? 'bg-blue-100 text-blue-800' 
                            : 'bg-purple-100 text-purple-800'
                        }`}>
                          {exam.exam_type === 'mcq' ? 'Multiple Choice' : 'Subjective'}
                        </span>
                        
                        {exam.status === 'active' && (
                          <button
                            onClick={() => startExam(exam.id)}
                            className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
                          >
                            <Play className="h-3 w-3 mr-1" />
                            Start Exam
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        )}

        {activeTab === 'available' && (
          <div>
            {console.log('Rendering available tab with exams:', availableExams)}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {availableExams.length === 0 ? (
                <div className="col-span-full text-center py-12">
                  <Search className="mx-auto h-12 w-12 text-gray-400" />
                  <h3 className="mt-2 text-sm font-medium text-gray-900">No available exams</h3>
                  <p className="mt-1 text-sm text-gray-500">
                    No new exams are available for registration at the moment.
                  </p>
                  <div className="mt-4 text-xs text-gray-400">
                    Debug: availableExams.length = {availableExams.length}
                  </div>
                </div>
              ) : (
                availableExams.map((exam) => {
                  console.log('Rendering exam:', exam.id, exam.title);
                  return (
                    <div key={exam.id} className="bg-white overflow-hidden shadow rounded-lg">
                      <div className="px-4 py-5 sm:p-6">
                        <div className="flex items-center justify-between mb-4">
                          <h3 className="text-lg font-medium text-gray-900 truncate">
                            {exam.title}
                          </h3>
                          <div className="flex items-center text-sm text-green-600">
                            <CheckCircle className="h-4 w-4 mr-1" />
                            Available
                          </div>
                        </div>
                        
                        <p className="text-sm text-gray-500 mb-4 line-clamp-2">
                          {exam.description || 'No description available'}
                        </p>
                        
                        <div className="flex items-center justify-between text-sm text-gray-500 mb-4">
                          <div className="flex items-center">
                            <Clock className="h-4 w-4 mr-1" />
                            {exam.duration_minutes} minutes
                          </div>
                          <div className="flex items-center">
                            <Trophy className="h-4 w-4 mr-1" />
                            {exam.total_points} points
                          </div>
                        </div>
                        
                        <div className="flex items-center justify-between">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            exam.exam_type === 'mcq' 
                              ? 'bg-blue-100 text-blue-800' 
                              : 'bg-purple-100 text-purple-800'
                          }`}>
                            {exam.exam_type === 'mcq' ? 'Multiple Choice' : 'Subjective'}
                          </span>
                          
                          <button
                            onClick={() => handleRegisterForExam(exam)}
                            className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                          >
                            <UserPlus className="h-3 w-3 mr-1" />
                            Register
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}

        {activeTab === 'registrations' && (
          <div className="bg-white shadow overflow-hidden sm:rounded-md">
            {registrations.length === 0 ? (
              <div className="text-center py-12">
                <Calendar className="mx-auto h-12 w-12 text-gray-400" />
                <h3 className="mt-2 text-sm font-medium text-gray-900">No registrations yet</h3>
                <p className="mt-1 text-sm text-gray-500">
                  Your exam registration requests will appear here.
                </p>
              </div>
            ) : (
              <ul className="divide-y divide-gray-200">
                {registrations.map((registration) => {
                  const statusInfo = getRegistrationStatus(registration.status);
                  const StatusIcon = statusInfo.icon;
                  
                  return (
                    <li key={registration.id} className="px-6 py-4">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="flex items-center justify-between">
                            <p className="text-sm font-medium text-gray-900">
                              Registration Request
                            </p>
                            <div className="ml-2 flex-shrink-0 flex">
                              <p className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                                registration.status === 'approved' 
                                  ? 'bg-green-100 text-green-800'
                                  : registration.status === 'pending'
                                  ? 'bg-yellow-100 text-yellow-800'
                                  : 'bg-red-100 text-red-800'
                              }`}>
                                <StatusIcon className="h-3 w-3 mr-1" />
                                {statusInfo.text}
                              </p>
                            </div>
                          </div>
                          <div className="mt-2 sm:flex sm:justify-between">
                            <div className="sm:flex">
                              <p className="flex items-center text-sm text-gray-500">
                                Requested: {new Date(registration.requested_at).toLocaleDateString()}
                              </p>
                            </div>
                            {registration.reviewed_at && (
                              <div className="mt-2 flex items-center text-sm text-gray-500 sm:mt-0">
                                <p>
                                  Reviewed: {new Date(registration.reviewed_at).toLocaleDateString()}
                                </p>
                              </div>
                            )}
                          </div>
                          {registration.notes && (
                            <div className="mt-2">
                              <p className="text-sm text-gray-600">
                                <strong>Notes:</strong> {registration.notes}
                              </p>
                            </div>
                          )}
                        </div>
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        )}

        {activeTab === 'results' && (
          <div className="bg-white shadow overflow-hidden sm:rounded-md">
            {results.length === 0 ? (
              <div className="text-center py-12">
                <Trophy className="mx-auto h-12 w-12 text-gray-400" />
                <h3 className="mt-2 text-sm font-medium text-gray-900">No results yet</h3>
                <p className="mt-1 text-sm text-gray-500">
                  Your exam results will appear here once released.
                </p>
              </div>
            ) : (
              <ul className="divide-y divide-gray-200">
                {results.map((result) => (
                  <li key={result.id} className="px-6 py-4">
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center justify-between">
                          <p className="text-sm font-medium text-gray-900">
                            Exam Result
                          </p>
                          <div className="ml-2 flex-shrink-0 flex">
                            <p className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                              result.percentage >= 80 
                                ? 'bg-green-100 text-green-800'
                                : result.percentage >= 60
                                ? 'bg-yellow-100 text-yellow-800'
                                : 'bg-red-100 text-red-800'
                            }`}>
                              {result.percentage.toFixed(1)}%
                            </p>
                          </div>
                        </div>
                        <div className="mt-2 sm:flex sm:justify-between">
                          <div className="sm:flex">
                            <p className="flex items-center text-sm text-gray-500">
                              Score: {result.total_score} / {result.max_score}
                            </p>
                          </div>
                          <div className="mt-2 flex items-center text-sm text-gray-500 sm:mt-0">
                            <p>
                              Released: {new Date(result.released_at).toLocaleDateString()}
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>

      {/* Registration Modal */}
      {showRegisterModal && (
        <ExamRegistrationModal
          exam={selectedExam}
          onClose={() => {
            setShowRegisterModal(false);
            setSelectedExam(null);
          }}
          onSubmit={handleRegisterSubmit}
        />
      )}
    </div>
  );
};

// Registration Modal Component
const ExamRegistrationModal = ({ exam, onClose, onSubmit }) => {
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      await onSubmit(notes);
    } catch (error) {
      // Error handling is done in parent component
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-20 mx-auto p-5 border w-11/12 md:w-3/4 lg:w-1/2 shadow-lg rounded-md bg-white">
        <div className="mt-3">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-medium text-gray-900">Register for Exam</h3>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              <span className="sr-only">Close</span>
              ✕
            </button>
          </div>

          <div className="mb-4 p-4 bg-gray-50 rounded-lg">
            <h4 className="font-medium text-gray-900">{exam.title}</h4>
            <p className="text-sm text-gray-600 mt-1">{exam.description}</p>
            <div className="mt-2 flex items-center space-x-4 text-sm text-gray-500">
              <span className="flex items-center">
                <Clock className="h-4 w-4 mr-1" />
                {exam.duration_minutes} minutes
              </span>
              <span className="flex items-center">
                <Trophy className="h-4 w-4 mr-1" />
                {exam.total_points} points
              </span>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Additional Notes (Optional)
              </label>
              <textarea
                rows={3}
                className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Any additional information or questions for the examiner..."
              />
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
                <Send className="h-4 w-4 mr-2 inline" />
                {loading ? 'Submitting...' : 'Submit Registration'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default StudentDashboard;