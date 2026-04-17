import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import DashboardPage from './pages/DashboardPage'
import ProjectsPage from './pages/ProjectsPage'
import ProjectDetailPage from './pages/ProjectDetailPage'
import AuditPage from './pages/AuditPage'
import AuditDetailPage from './pages/AuditDetailPage'
import RuntimePage from './pages/RuntimePage'
import ReceiptsPage from './pages/ReceiptsPage'
import ReceiptDetailPage from './pages/ReceiptDetailPage'

const isAuthenticated = () => !!localStorage.getItem('token')

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />
  }
  return <>{children}</>
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
        <Route path="/projects" element={<ProtectedRoute><ProjectsPage /></ProtectedRoute>} />
        <Route path="/projects/:id" element={<ProtectedRoute><ProjectDetailPage /></ProtectedRoute>} />
        <Route path="/audit/new" element={<ProtectedRoute><AuditPage /></ProtectedRoute>} />
        <Route path="/audit/:id" element={<ProtectedRoute><AuditDetailPage /></ProtectedRoute>} />
        <Route path="/runtime" element={<ProtectedRoute><RuntimePage /></ProtectedRoute>} />
        <Route path="/receipts" element={<ProtectedRoute><ReceiptsPage /></ProtectedRoute>} />
        <Route path="/receipts/:id" element={<ProtectedRoute><ReceiptDetailPage /></ProtectedRoute>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
