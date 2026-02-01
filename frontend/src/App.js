import React, { useState, useEffect } from 'react';
import { AlertCircle, CheckCircle, Upload, FileText, Clock, XCircle, Eye, Award, FileCheck, AlertTriangle, Shield, LogOut, User as UserIcon } from 'lucide-react';
import './App.css';

const API_BASE = 'http://localhost:8000/api';

const KYCOnboardingApp = () => {
  // Authentication state
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const [authView, setAuthView] = useState('login'); // 'login' or 'register'
  
  // Login/Register form state
  const [authForm, setAuthForm] = useState({
    email: '',
    password: '',
    full_name: '',
    role: 'MAKER'
  });

  // Application state
  const [activeTab, setActiveTab] = useState('create');
  const [cases, setCases] = useState([]);
  const [selectedCase, setSelectedCase] = useState(null);
  const [loading, setLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState({});
  const [error, setError] = useState('');

  // Form state for new case
  const [formData, setFormData] = useState({
    customerName: '',
    dob: '',
    address: '',
    email: '',
    phone: ''
  });

  const [documents, setDocuments] = useState({
    pan: null,
    aadhaar: null,
    passport: null
  });

  // Check for existing token on mount
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      verifyToken(token);
    }
  }, []);

  useEffect(() => {
    if (isAuthenticated) {
      fetchCases();
    }
  }, [isAuthenticated]);

  const verifyToken = async (token) => {
    try {
      const response = await fetch(`${API_BASE}/auth/me`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const userData = await response.json();
        setCurrentUser(userData);
        setIsAuthenticated(true);
      } else {
        localStorage.removeItem('token');
      }
    } catch (error) {
      console.error('Token verification failed:', error);
      localStorage.removeItem('token');
    }
  };

  const handleAuthSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const endpoint = authView === 'login' ? '/auth/login' : '/auth/register';
      const payload = authView === 'login' 
        ? { email: authForm.email, password: authForm.password }
        : authForm;

      const response = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await response.json();


      if (response.ok) {
        if (authView === 'login') {
          localStorage.setItem('token', data.access_token);
          setCurrentUser(data.user);
          setIsAuthenticated(true);
        } else {
          setAuthView('login');
          alert('Registration successful! Please login.');
        }
        setAuthForm({ email: '', password: '', full_name: '', role: 'MAKER' });
      } else {
        setError(data.detail || 'Authentication failed');
      }
    } catch (error) {
      setError('Network error. Please try again.');
      console.error('Auth error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setIsAuthenticated(false);
    setCurrentUser(null);
    setCases([]);
    setActiveTab('create');
  };

  const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    };
  };

  const fetchCases = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/cases`, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const data = await response.json();
        setCases(data);
      } else if (response.status === 401) {
        handleLogout();
      }
    } catch (error) {
      console.error('Error fetching cases:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleAuthInputChange = (e) => {
    setAuthForm({ ...authForm, [e.target.name]: e.target.value });
  };

  const handleFileUpload = async (docType, e, caseId = null) => {
    const file = e.target.files[0];
    if (!file) return;

    setDocuments({ ...documents, [docType]: file });

    if (caseId) {
      await uploadDocument(caseId, docType, file);
    }
  };

  const uploadDocument = async (caseId, docType, file) => {
    const formDataToSend = new FormData();
    formDataToSend.append('doc_type', docType);
    formDataToSend.append('file', file);

    try {
      setUploadProgress({ ...uploadProgress, [docType]: 'uploading' });
      
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_BASE}/cases/${caseId}/upload`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formDataToSend
      });

      if (response.ok) {
        const result = await response.json();
        setUploadProgress({ ...uploadProgress, [docType]: 'success' });
        
        const riskInfo = result.risk_assessment || {};
        alert(`✅ Document processed!\n\nOCR Confidence: ${(result.ocr_confidence * 100).toFixed(1)}%\nData Match: ${(result.data_match_score * 100).toFixed(1)}%\n\n🛡️ Risk Assessment:\nRisk Level: ${riskInfo.risk_level || 'N/A'}\nRisk Score: ${riskInfo.risk_score || 'N/A'}/100\nValid: ${riskInfo.is_valid ? 'Yes' : 'No'}\nAnomalies: ${riskInfo.anomalies_count || 0}`);
        
        fetchCases();
      } else {
        const error = await response.json();
        setUploadProgress({ ...uploadProgress, [docType]: 'error' });
        alert(`Error: ${error.detail}`);
      }
    } catch (error) {
      setUploadProgress({ ...uploadProgress, [docType]: 'error' });
      console.error('Error uploading document:', error);
    }
  };

  const createCase = async () => {
    if (!formData.customerName || !formData.dob || !formData.address) {
      alert('Please fill all required fields');
      return;
    }

    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/cases`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          customer_name: formData.customerName,
          dob: formData.dob,
          address: formData.address,
          email: formData.email,
          phone: formData.phone
        })
      });

      if (response.ok) {
        const newCase = await response.json();
        
        for (const [docType, file] of Object.entries(documents)) {
          if (file) {
            await uploadDocument(newCase.id, docType, file);
          }
        }
        
        setFormData({ customerName: '', dob: '', address: '', email: '', phone: '' });
        setDocuments({ pan: null, aadhaar: null, passport: null });
        setUploadProgress({});
        
        alert('✅ Case created successfully!');
        setActiveTab('list');
        fetchCases();
      } else {
        const error = await response.json();
        alert(`Error: ${error.detail}`);
      }
    } catch (error) {
      console.error('Error creating case:', error);
      alert('Failed to create case');
    } finally {
      setLoading(false);
    }
  };

  const submitCase = async (caseId) => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/cases/${caseId}/submit`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({})
      });

      if (response.ok) {
        alert('✅ Case submitted for review!');
        fetchCases();
      } else {
        const error = await response.json();
        alert(`Error: ${error.detail}`);
      }
    } catch (error) {
      console.error('Error submitting case:', error);
    } finally {
      setLoading(false);
    }
  };

  const reviewCase = async (caseId, action) => {
    const endpoint = action === 'approve' ? 'approve' : 'reject';

    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/cases/${caseId}/${endpoint}`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          comments: action === 'reject' ? 'Documents require verification' : 'All checks passed'
        })
      });

      if (response.ok) {
        alert(`✅ Case ${action}d successfully!`);
        setSelectedCase(null);
        fetchCases();
      } else {
        const error = await response.json();
        alert(`Error: ${error.detail}`);
      }
    } catch (error) {
      console.error(`Error ${action}ing case:`, error);
    } finally {
      setLoading(false);
    }
  };

  // ... (Include all the rendering helper functions from previous version)
  const getRiskLevelColor = (level) => {
    const colors = {
      'VERY_LOW': 'risk-very-low',
      'LOW': 'risk-low',
      'MEDIUM': 'risk-medium',
      'HIGH': 'risk-high',
      'VERY_HIGH': 'risk-very-high'
    };
    return colors[level] || 'risk-medium';
  };

  const getConfidenceColor = (score) => {
    if (score >= 0.8) return 'confidence-high';
    if (score >= 0.6) return 'confidence-medium';
    return 'confidence-low';
  };

  const renderOCRResults = (ocrResults) => {
    if (!ocrResults || Object.keys(ocrResults).length === 0) {
      return <p className="no-data">No OCR data available</p>;
    }

    return (
      <div className="ocr-results-container">
        {Object.entries(ocrResults).map(([docType, data]) => (
          <div key={docType} className="ocr-result-card">
            <div className="ocr-header">
              <h5 className="doc-type">{docType.toUpperCase()}</h5>
              <div className="confidence-badge">
                <Award size={16} />
                <span className={getConfidenceColor(data.confidence_score)}>
                  {(data.confidence_score * 100).toFixed(1)}% Confidence
                </span>
              </div>
            </div>

            {data.extracted_fields && (
              <div className="extracted-fields">
                <p className="section-title">Extracted Fields:</p>
                <div className="fields-grid">
                  {Object.entries(data.extracted_fields).map(([key, value]) => (
                    value && (
                      <div key={key} className="field-item">
                        <span className="field-label">{key}:</span>
                        <span className="field-value">{value}</span>
                      </div>
                    )
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    );
  };

  // Login/Register Screen
  if (!isAuthenticated) {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <h1>KYC Onboarding System</h1>
          <p className="auth-subtitle">Secure Login & Registration</p>

          <div className="auth-tabs">
            <button
              className={authView === 'login' ? 'active' : ''}
              onClick={() => setAuthView('login')}
            >
              Login
            </button>
            <button
              className={authView === 'register' ? 'active' : ''}
              onClick={() => setAuthView('register')}
            >
              Register
            </button>
          </div>

          <form onSubmit={handleAuthSubmit} className="auth-form">
            {authView === 'register' && (
              <div className="form-group">
                <label>Full Name *</label>
                <input
                  type="text"
                  name="full_name"
                  value={authForm.full_name}
                  onChange={handleAuthInputChange}
                  required
                  placeholder="Enter your full name"
                />
              </div>
            )}

            <div className="form-group">
              <label>Email *</label>
              <input
                type="email"
                name="email"
                value={authForm.email}
                onChange={handleAuthInputChange}
                required
                placeholder="your@email.com"
              />
            </div>

            <div className="form-group">
              <label>Password *</label>
              <input
                type="password"
                name="password"
                value={authForm.password}
                onChange={handleAuthInputChange}
                required
                placeholder="Enter password"
                minLength={6}
                maxLength={72}
              />
              <small style={{color: '#6b7280', fontSize: '0.75rem'}}>
                6-72 characters
              </small>
            </div>

            {authView === 'register' && (
              <div className="form-group">
                <label>Role *</label>
                <select
                  name="role"
                  value={authForm.role}
                  onChange={handleAuthInputChange}
                  required
                >
                  <option value="MAKER">MAKER (Create Cases)</option>
                  <option value="CHECKER">CHECKER (Review Cases)</option>
                </select>
              </div>
            )}

            {error && (
              <div className="error-message">
                <AlertCircle size={16} />
                {error}
              </div>
            )}

            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Please wait...' : (authView === 'login' ? 'Login' : 'Register')}
            </button>
          </form>
        </div>
      </div>
    );
  }

  // Main Application (after login)
  return (
    <div className="app-container">
      <header className="app-header">
        <div className="header-content">
          <div className="header-left">
            <h1>KYC Onboarding System</h1>
            <p className="subtitle">with OCR & NLP Processing</p>
          </div>
          <div className="header-right">
            <div className="user-info">
              <UserIcon size={20} />
              <div>
                <div className="user-name">{currentUser?.full_name}</div>
                <div className={`user-role ${currentUser?.role?.toLowerCase()}`}>
                  {currentUser?.role}
                </div>
              </div>
            </div>
            <button onClick={handleLogout} className="btn btn-secondary btn-sm">
              <LogOut size={16} />
              Logout
            </button>
          </div>
        </div>
      </header>

      {loading && (
        <div className="loading-overlay">
          <div className="loading-content">Processing...</div>
        </div>
      )}

      <main className="main-content">
        <div className="content-card">
          <div className="tabs">
            <button
              className={`tab ${activeTab === 'create' ? 'active' : ''}`}
              onClick={() => setActiveTab('create')}
            >
              Create Case
            </button>
            <button
              className={`tab ${activeTab === 'list' ? 'active' : ''}`}
              onClick={() => setActiveTab('list')}
            >
              All Cases ({cases.length})
            </button>
          </div>

          <div className="tab-content">
            {activeTab === 'create' && currentUser?.role === 'MAKER' && (
              <div className="form-container">
                <h2>Customer Information</h2>
                
                <div className="form-grid">
                  <div className="form-group">
                    <label>Customer Name *</label>
                    <input
                      type="text"
                      name="customerName"
                      value={formData.customerName}
                      onChange={handleInputChange}
                      placeholder="Enter full name"
                    />
                  </div>
                  <div className="form-group">
                    <label>Date of Birth *</label>
                    <input
                      type="date"
                      name="dob"
                      value={formData.dob}
                      onChange={handleInputChange}
                    />
                  </div>
                  <div className="form-group full-width">
                    <label>Address *</label>
                    <textarea
                      name="address"
                      value={formData.address}
                      onChange={handleInputChange}
                      rows="3"
                      placeholder="Enter complete address"
                    />
                  </div>
                  <div className="form-group">
                    <label>Email</label>
                    <input
                      type="email"
                      name="email"
                      value={formData.email}
                      onChange={handleInputChange}
                      placeholder="email@example.com"
                    />
                  </div>
                  <div className="form-group">
                    <label>Phone</label>
                    <input
                      type="tel"
                      name="phone"
                      value={formData.phone}
                      onChange={handleInputChange}
                      placeholder="+91 1234567890"
                    />
                  </div>
                </div>

                <h2 style={{marginTop: '2rem'}}>KYC Documents (with OCR)</h2>
                
                <div className="documents-grid">
                  {['pan', 'aadhaar', 'passport'].map(docType => (
                    <div key={docType} className="document-upload">
                      <label className="upload-label">{docType.toUpperCase()}</label>
                      <div className="upload-area">
                        <input
                          type="file"
                          onChange={(e) => handleFileUpload(docType, e)}
                          id={`${docType}-upload`}
                          accept=".pdf,.jpg,.jpeg,.png"
                          style={{display: 'none'}}
                        />
                        <label htmlFor={`${docType}-upload`} className="upload-button">
                          <Upload size={32} />
                          <span>
                            {documents[docType] ? documents[docType].name : `Upload ${docType.toUpperCase()}`}
                          </span>
                          {uploadProgress[docType] === 'success' && (
                            <div className="upload-success">✓ Processed</div>
                          )}
                        </label>
                      </div>
                    </div>
                  ))}
                </div>

                <button
                  onClick={createCase}
                  disabled={loading}
                  className="btn btn-primary"
                  style={{marginTop: '1.5rem'}}
                >
                  Create Case with OCR
                </button>
              </div>
            )}

            {activeTab === 'create' && currentUser?.role === 'CHECKER' && (
              <div className="empty-state">
                <AlertCircle size={48} />
                <p>Only MAKER users can create new cases.</p>
              </div>
            )}

            {activeTab === 'list' && (
              <div className="cases-list">
                {cases.length === 0 && (
                  <div className="empty-state">No cases found</div>
                )}
                
                {cases.map(caseItem => (
                  <div key={caseItem.id} className="case-card">
                    <div className="case-header">
                      <div className="case-info">
                        <div className="case-title-row">
                          <h3>{caseItem.customer_name}</h3>
                          <span className={`status-badge status-${caseItem.status.toLowerCase()}`}>
                            {caseItem.status === 'DRAFT' && <FileText size={14} />}
                            {caseItem.status === 'SUBMITTED' && <Upload size={14} />}
                            {caseItem.status === 'AI_REVIEWED' && <Clock size={14} />}
                            {caseItem.status === 'CHECKER_APPROVED' && <CheckCircle size={14} />}
                            {caseItem.status === 'CHECKER_REJECTED' && <XCircle size={14} />}
                            {caseItem.status}
                          </span>
                          {caseItem.ai_score && (
                            <span className="ai-score">
                              <Award size={14} />
                              AI: {caseItem.ai_score}/100
                            </span>
                          )}
                          {caseItem.risk_score !== undefined && (
                            <span className={`risk-badge ${getRiskLevelColor(caseItem.risk_level)}`}>
                              <Shield size={14} />
                              Risk: {caseItem.risk_score}/100
                            </span>
                          )}
                        </div>
                        <div className="case-details">
                          <p>Case ID: {caseItem.id}</p>
                          <p>Created by: {caseItem.created_by_name}</p>
                          <p>Created: {new Date(caseItem.created_at).toLocaleString()}</p>
                          {caseItem.data_match_score > 0 && (
                            <p className={getConfidenceColor(caseItem.data_match_score)}>
                              Data Match: {(caseItem.data_match_score * 100).toFixed(1)}%
                            </p>
                          )}
                        </div>
                      </div>
                      
                      <div className="case-actions">
                        {currentUser?.role === 'MAKER' && caseItem.status === 'DRAFT' && caseItem.created_by === currentUser.id && (
                          <button onClick={() => submitCase(caseItem.id)} className="btn btn-primary btn-sm">
                            Submit
                          </button>
                        )}
                        
                        {currentUser?.role === 'CHECKER' && (caseItem.status === 'SUBMITTED' || caseItem.status === 'AI_REVIEWED') && (
                          <>
                            <button onClick={() => reviewCase(caseItem.id, 'approve')} className="btn btn-success btn-sm">
                              Approve
                            </button>
                            <button onClick={() => reviewCase(caseItem.id, 'reject')} className="btn btn-danger btn-sm">
                              Reject
                            </button>
                          </>
                        )}
                        
                        <button
                          onClick={() => setSelectedCase(selectedCase?.id === caseItem.id ? null : caseItem)}
                          className="btn btn-secondary btn-sm"
                        >
                          <Eye size={16} />
                          {selectedCase?.id === caseItem.id ? 'Hide' : 'Details'}
                        </button>
                      </div>
                    </div>
                    
                    {selectedCase?.id === caseItem.id && (
                      <div className="case-details-expanded">
                        {caseItem.ocr_results && Object.keys(caseItem.ocr_results).length > 0 && (
                          <div className="details-section">
                            <h4>
                              <FileCheck size={18} />
                              OCR Results
                            </h4>
                            {renderOCRResults(caseItem.ocr_results)}
                          </div>
                        )}

                        <div className="details-section">
                          <h4>Audit Trail</h4>
                          <div className="audit-trail">
                            {caseItem.audit_trail.map((audit, idx) => (
                              <div key={idx} className="audit-item">
                                <div className="audit-time">
                                  {new Date(audit.timestamp).toLocaleString()}
                                </div>
                                <div className="audit-details">
                                  <strong>{audit.action}</strong> by {audit.by} ({audit.role})
                                  {audit.comments && <p className="audit-comment">{audit.comments}</p>}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};

export default KYCOnboardingApp;