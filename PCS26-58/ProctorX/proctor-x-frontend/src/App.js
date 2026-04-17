// Import React library for building the user interface
import React from 'react';
// Import React Router components for client-side routing
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
// Import authentication context for managing user authentication state
import { AuthProvider, useAuth } from './context/AuthContext';
// Import notification context for displaying app-wide notifications
import { NotificationProvider } from './context/NotificationContext';
// Import page components
import Login from './components/auth/Login';
import Register from './components/auth/Register';
import StudentDashboard from './components/student/StudentDashboard';
import ExaminerDashboard from './components/examiner/ExaminerDashboard';
import ExamTaking from './components/student/ExamTaking';
// Import common components
import Navbar from './components/common/Navbar';
import Notifications from './components/common/Notifications';
// Import CSS styles for the App component
import './App.css';

/**
 * ProtectedRoute component - handles route protection based on authentication and role
 * 
 * @param {Object} props - Component props
 * @param {React.ReactNode} props.children - Child components to render if authorized
 * @param {string} props.requiredRole - Required user role to access the route
 * @returns {React.ReactNode} - Either children, redirect to login, or unauthorized page
 */
function ProtectedRoute({ children, requiredRole }) {
  const { user, isAuthenticated } = useAuth();
  
  // If user is not authenticated, redirect to login page
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  // If specific role is required and user doesn't have it, show unauthorized page
  if (requiredRole && user?.role !== requiredRole) {
    return <Navigate to="/unauthorized" replace />;
  }
  
  // User is authenticated and has required role, render children
  return children;
}

/**
 * AppContent component - Main application content with routing logic
 * Handles all route definitions and navigation based on user authentication status and role
 * 
 * @returns {React.ReactNode} - Rendered application content with routes
 */
function AppContent() {
  const { isAuthenticated, user } = useAuth();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Show navbar only when user is authenticated */}
      {isAuthenticated && <Navbar />}
      {/* Global notifications component */}
      <Notifications />
      
      <Routes>
        {/* Public routes - accessible without authentication */}
        <Route 
          path="/login" 
          element={
            // If already authenticated, redirect to appropriate dashboard
            isAuthenticated ? 
            <Navigate to={user?.role === 'student' ? '/student' : '/examiner'} replace /> : 
            <Login />
          } 
        />
        <Route 
          path="/register" 
          element={
            // If already authenticated, redirect to appropriate dashboard
            isAuthenticated ? 
            <Navigate to={user?.role === 'student' ? '/student' : '/examiner'} replace /> : 
            <Register />
          } 
        />
        
        {/* Protected routes - require authentication and specific roles */}
        <Route 
          path="/student" 
          element={
            <ProtectedRoute requiredRole="student">
              <StudentDashboard />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/student/exam/:examId" 
          element={
            <ProtectedRoute requiredRole="student">
              <ExamTaking />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/examiner" 
          element={
            <ProtectedRoute requiredRole="examiner">
              <ExaminerDashboard />
            </ProtectedRoute>
          } 
        />
        
        {/* Default redirects - handle root path routing */}
        <Route 
          path="/" 
          element={
            <Navigate to={
              isAuthenticated ? 
              // Redirect based on user role if authenticated
              (user?.role === 'student' ? '/student' : '/examiner') : 
              // Redirect to login if not authenticated
              '/login'
            } replace />
          } 
        />
        
        {/* Error pages - 403 Unauthorized and 404 Not Found */}
        <Route 
          path="/unauthorized" 
          element={
            <div className="min-h-screen flex items-center justify-center">
              <div className="text-center">
                <h1 className="text-2xl font-bold text-red-600">Unauthorized Access</h1>
                <p className="text-gray-600">You don't have permission to access this page.</p>
              </div>
            </div>
          } 
        />
        <Route 
          path="*" 
          element={
            <div className="min-h-screen flex items-center justify-center">
              <div className="text-center">
                <h1 className="text-2xl font-bold text-gray-800">Page Not Found</h1>
                <p className="text-gray-600">The page you're looking for doesn't exist.</p>
              </div>
            </div>
          } 
        />
      </Routes>
    </div>
  );
}

/**
 * Main App component - Root component of the application
 * Sets up the router and context providers for the entire application
 * 
 * @returns {React.ReactNode} - Wrapped application with providers
 */
function App() {
  return (
    // Router provides client-side routing functionality
    <Router>
      {/* AuthProvider manages user authentication state globally */}
      <AuthProvider>
        {/* NotificationProvider manages app-wide notifications */}
        <NotificationProvider>
          {/* AppContent contains all the routes and main application logic */}
          <AppContent />
        </NotificationProvider>
      </AuthProvider>
    </Router>
  );
}

// Export the App component as the default export
export default App;