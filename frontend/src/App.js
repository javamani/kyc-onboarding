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

  // Modified uploadDocument to return result instead of showing alerts immediately
  const uploadDocument = async (caseId, docType, file) => {
    const formDataToSend = new FormData();
    formDataToSend.append('doc_type', docType);
    formDataToSend.append('file', file);

    try {
      setUploadProgress(prev => ({ ...prev, [docType]: 'uploading' }));
      
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_BASE}/cases/${caseId}/upload`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formDataToSend
      });

      if (response.ok) {
        const result = await response.json();
        setUploadProgress(prev => ({ ...prev, [docType]: 'success' }));
        return { success: true, data: result, docType };
      } else {
        const error = await response.json();
        setUploadProgress(prev => ({ ...prev, [docType]: 'error' }));
        return { success: false, error: error.detail || 'Upload failed', docType };
      }
    } catch (error) {
      setUploadProgress(prev => ({ ...prev, [docType]: 'error' }));
      console.error('Error uploading document:', error);
      return { success: false, error: error.message || 'Upload failed', docType };
    }
  };

  // Helper function to delete a case if uploads fail
  const deleteCase = async (caseId) => {
    try {
      const token = localStorage.getItem('token');
      await fetch(`${API_BASE}/cases/${caseId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      console.log(`Case ${caseId} deleted due to upload failure`);
    } catch (error) {
      console.error('Error deleting case:', error);
    }
  };

  // Modified createCase function with proper error handling
  const createCase = async () => {
    if (!formData.customerName || !formData.dob || !formData.address) {
      alert('Please fill all required fields');
      return;
    }

    // Check if at least one document is selected
    const hasDocuments = Object.values(documents).some(doc => doc !== null);
    if (!hasDocuments) {
      alert('⚠️ Please upload at least one document before creating the case');
      return;
    }

    let createdCaseId = null;

    try {
      setLoading(true);
      
      // Step 1: Create the case
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

      if (!response.ok) {
        const error = await response.json();
        alert(`Error creating case: ${error.detail}`);
        return;
      }

      const newCase = await response.json();
      createdCaseId = newCase.id;
      
      // Step 2: Upload all documents and track results
      const uploadResults = [];
      let allUploadsSuccessful = true;

      for (const [docType, file] of Object.entries(documents)) {
        if (file) {
          const result = await uploadDocument(createdCaseId, docType, file);
          uploadResults.push(result);
          
          if (!result.success) {
            allUploadsSuccessful = false;
          }
        }
      }

      // Step 3: Check if all uploads were successful
      if (!allUploadsSuccessful) {
        // Delete the case if any upload failed
        await deleteCase(createdCaseId);
        
        // Show detailed error message
        const failedUploads = uploadResults
          .filter(r => !r.success)
          .map(r => `${r.docType.toUpperCase()}: ${r.error}`)
          .join('\n');
        
        alert(`❌ Case creation cancelled due to document upload failures:\n\n${failedUploads}\n\nPlease try again.`);
        
        // Reset upload progress
        setUploadProgress({});
        return;
      }

      // Step 4: All uploads successful - show success summary
      const successSummary = uploadResults
        .filter(r => r.success)
        .map(r => {
          const riskInfo = r.data.risk_assessment || {};
          return `✅ ${r.docType.toUpperCase()}:\n  OCR Confidence: ${(r.data.ocr_confidence * 100).toFixed(1)}%\n  Data Match: ${(r.data.data_match_score * 100).toFixed(1)}%\n  Risk Level: ${riskInfo.risk_level || 'N/A'} (${riskInfo.risk_score || 'N/A'}/100)`;
        })
        .join('\n\n');

      alert(`🎉 Case created successfully!\n\nCase ID: ${createdCaseId}\n\n${successSummary}`);

      // Reset form and navigate to list
      setFormData({ customerName: '', dob: '', address: '', email: '', phone: '' });
      setDocuments({ pan: null, aadhaar: null, passport: null });
      setUploadProgress({});
      setActiveTab('list');
      fetchCases();

    } catch (error) {
      console.error('Error creating case:', error);
      
      // If case was created but something went wrong, delete it
      if (createdCaseId) {
        await deleteCase(createdCaseId);
      }
      
      alert('❌ Failed to create case. Please try again.');
      setUploadProgress({});
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
        alert('✅ Case submitted successfully for review!');
        fetchCases();
      } else {
        const error = await response.json();
        alert(`Error: ${error.detail}`);
      }
    } catch (error) {
      console.error('Error submitting case:', error);
      alert('Failed to submit case');
    } finally {
      setLoading(false);
    }
  };

  const reviewCase = async (caseId, action) => {
    const comments = prompt(`Enter ${action} comments (optional):`);
    
    try {
      setLoading(true);
      const endpoint = action === 'approve' ? 'approve' : 'reject';
      const response = await fetch(`${API_BASE}/cases/${caseId}/${endpoint}`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          action: action.toUpperCase(),
          comments: comments || ''
        })
      });

      if (response.ok) {
        alert(`Case ${action}d successfully!`);
        fetchCases();
      } else {
        const error = await response.json();
        alert(`Error: ${error.detail}`);
      }
    } catch (error) {
      console.error('Error reviewing case:', error);
      alert('Failed to review case');
    } finally {
      setLoading(false);
    }
  };

  const returnToMaker = async (caseId) => {
    const comments = prompt('Enter reason for returning to maker (required - explain what needs to be fixed):');
    
    if (!comments || comments.trim() === '') {
      alert('Please provide a reason for returning the case to the maker.');
      return;
    }
    
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/cases/${caseId}/return-to-maker`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          comments: comments
        })
      });

      if (response.ok) {
        alert('✅ Case returned to maker for corrections.\n\nThe maker will be able to reupload documents and resubmit.');
        fetchCases();
      } else {
        const error = await response.json();
        alert(`Error: ${error.detail}`);
      }
    } catch (error) {
      console.error('Error returning case:', error);
      alert('Failed to return case to maker');
    } finally {
      setLoading(false);
    }
  };

  const getConfidenceColor = (score) => {
    if (score >= 0.9) return 'confidence-high';
    if (score >= 0.7) return 'confidence-medium';
    return 'confidence-low';
  };

  const getRiskLevelColor = (level) => {
    const colors = {
      'LOW': 'risk-low',
      'MEDIUM': 'risk-medium',
      'HIGH': 'risk-high',
      'CRITICAL': 'risk-critical'
    };
    return colors[level] || '';
  };

  const renderOCRResults = (ocrResults) => {
    return (
      <div className="ocr-results-container">
        {Object.entries(ocrResults).map(([docType, data]) => (
          <div key={docType} className="ocr-result-card">
            <div className="ocr-header">
              <div className="doc-type">{docType.toUpperCase()} Document</div>
              <div className={`confidence-badge confidence-${data.confidence_score > 0.8 ? 'high' : data.confidence_score > 0.6 ? 'medium' : 'low'}`}>
                <FileCheck size={14} />
                {(data.confidence_score * 100).toFixed(1)}% Confidence
              </div>
            </div>

            {/* Extracted Fields */}
            {data.extracted_fields && Object.keys(data.extracted_fields).length > 0 && (
              <div className="extracted-fields">
                <div className="section-title">EXTRACTED DATA</div>
                <div className="fields-grid">
                  {Object.entries(data.extracted_fields).map(([key, value]) => (
                    <div key={key} className="field-item">
                      <span className="field-label">{key.replace(/_/g, ' ')}:</span>
                      <span className="field-value">{value || 'N/A'}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Validation Results */}
            {data.validation && (
              <div className="validation-section">
                <div className="section-title">VALIDATION RESULTS</div>
                <div className="match-score">
                  Overall Match: 
                  <span className={getConfidenceColor(data.validation.overall_match_score)}>
                    {' '}{(data.validation.overall_match_score * 100).toFixed(1)}%
                  </span>
                </div>
                
                {data.validation.matches && Object.keys(data.validation.matches).length > 0 && (
                  <div className="validation-matches">
                    ✓ Matched Fields: {Object.keys(data.validation.matches).join(', ')}
                  </div>
                )}
                
                {data.validation.mismatches && Object.keys(data.validation.mismatches).length > 0 && (
                  <div className="validation-mismatches">
                    ✗ Mismatched Fields: {Object.keys(data.validation.mismatches).join(', ')}
                  </div>
                )}
              </div>
            )}

            {/* Quality Check Info */}
            {data.quality_check && data.quality_check.details && (
              <div className="quality-info">
                Quality: {data.quality_check.reason} 
                {data.quality_check.details.size && 
                  ` | Size: ${data.quality_check.details.size[0]}x${data.quality_check.details.size[1]}px`
                }
              </div>
            )}
          </div>
        ))}
      </div>
    );
  };

  // Authentication view
  if (!isAuthenticated) {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <h1>🔐 KYC Onboarding System</h1>
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
                <label>Full Name</label>
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
              <label>Email</label>
              <input
                type="email"
                name="email"
                value={authForm.email}
                onChange={handleAuthInputChange}
                required
                placeholder="Enter your email"
              />
            </div>

            <div className="form-group">
              <label>Password</label>
              <input
                type="password"
                name="password"
                value={authForm.password}
                onChange={handleAuthInputChange}
                required
                placeholder="Enter your password"
              />
            </div>

            {authView === 'register' && (
              <div className="form-group">
                <label>Role</label>
                <select
                  name="role"
                  value={authForm.role}
                  onChange={handleAuthInputChange}
                >
                  <option value="MAKER">Maker</option>
                  <option value="CHECKER">Checker</option>
                </select>
              </div>
            )}

            {error && (
              <div className="error-message">
                <AlertCircle size={16} />
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="btn btn-primary"
            >
              {loading ? 'Processing...' : authView === 'login' ? 'Login' : 'Register'}
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="header-content">
          <div className="header-left">
            <h1>🔐 KYC Onboarding System</h1>
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

      <main className="main-content">
        <div className="content-card">
          <div className="tabs">
            {currentUser?.role === 'MAKER' && (
              <button
                className={`tab ${activeTab === 'create' ? 'active' : ''}`}
                onClick={() => setActiveTab('create')}
              >
                <Upload size={18} />
                Create Case
              </button>
            )}
            <button
              className={`tab ${activeTab === 'list' ? 'active' : ''}`}
              onClick={() => setActiveTab('list')}
            >
              <FileText size={18} />
              All Cases
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
                          {uploadProgress[docType] === 'uploading' && (
                            <div className="upload-uploading">⏳ Uploading...</div>
                          )}
                          {uploadProgress[docType] === 'success' && (
                            <div className="upload-success">✓ Ready</div>
                          )}
                          {uploadProgress[docType] === 'error' && (
                            <div className="upload-error">✗ Error</div>
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
                  {loading ? 'Creating Case...' : 'Create Case with OCR'}
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
                          <span className={`status-badge status-${caseItem.status.toLowerCase().replace(/_/g, '_')}`}>
                            {caseItem.status === 'DRAFT' && <FileText size={14} />}
                            {caseItem.status === 'SUBMITTED' && <Upload size={14} />}
                            {caseItem.status === 'AI_REVIEWED' && <Clock size={14} />}
                            {caseItem.status === 'RETURNED_TO_MAKER' && <AlertCircle size={14} />}
                            {caseItem.status === 'CHECKER_APPROVED' && <CheckCircle size={14} />}
                            {caseItem.status === 'CHECKER_REJECTED' && <XCircle size={14} />}
                            {caseItem.status.replace(/_/g, ' ')}
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
                          {caseItem.status === 'RETURNED_TO_MAKER' && caseItem.return_reason && (
                            <p style={{color: '#f59e0b', fontWeight: '500', marginTop: '0.5rem'}}>
                              <AlertTriangle size={16} style={{verticalAlign: 'middle'}} />
                              {' '}Checker's feedback: {caseItem.return_reason}
                            </p>
                          )}
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

                        {/* MAKER can resubmit returned cases after fixing issues */}
                        {currentUser?.role === 'MAKER' && caseItem.status === 'RETURNED_TO_MAKER' && caseItem.created_by === currentUser.id && (
                          <button onClick={() => submitCase(caseItem.id)} className="btn btn-primary btn-sm">
                            Resubmit
                          </button>
                        )}
                        
                        {currentUser?.role === 'CHECKER' && (caseItem.status === 'SUBMITTED' || caseItem.status === 'AI_REVIEWED') && (
                          <>
                            <button onClick={() => reviewCase(caseItem.id, 'approve')} className="btn btn-success btn-sm">
                              Approve
                            </button>
                            <button onClick={() => returnToMaker(caseItem.id)} className="btn" style={{backgroundColor: '#f59e0b', color: 'white'}} title="Return to Maker for corrections">
                              Return to Maker
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
                        {/* AI-Extracted Data & Risk Assessment Section - Prominent for CHECKER */}
                        {currentUser?.role === 'CHECKER' && caseItem.validation_result && (
                          <div className="details-section">
                            <h4>
                              <Shield size={18} />
                              AI Risk Assessment & Validation
                            </h4>
                            
                            <div className="validation-container">
                              {/* Risk Overview */}
                              <div className="risk-overview">
                                <div className="risk-score-card">
                                  <Shield size={40} />
                                  <div>
                                    <div className="risk-score-label">Risk Score</div>
                                    <div className="risk-score">{caseItem.risk_score || 0}/100</div>
                                    <div className="risk-level">{caseItem.risk_level || 'UNKNOWN'}</div>
                                  </div>
                                </div>
                                
                                <div className="validation-status">
                                  <div className={caseItem.validation_result.is_valid ? 'status-valid' : 'status-invalid'}>
                                    {caseItem.validation_result.is_valid ? (
                                      <>
                                        <CheckCircle size={20} />
                                        Validation Passed
                                      </>
                                    ) : (
                                      <>
                                        <XCircle size={20} />
                                        Validation Failed
                                      </>
                                    )}
                                  </div>
                                  {caseItem.ai_score && (
                                    <div style={{marginTop: '0.5rem', fontSize: '0.875rem'}}>
                                      <Award size={16} style={{verticalAlign: 'middle'}} />
                                      <strong> AI Confidence: </strong>{caseItem.ai_score}/100
                                    </div>
                                  )}
                                  {caseItem.data_match_score > 0 && (
                                    <div style={{marginTop: '0.25rem', fontSize: '0.875rem'}}>
                                      <strong>Data Match: </strong>
                                      <span className={getConfidenceColor(caseItem.data_match_score)}>
                                        {(caseItem.data_match_score * 100).toFixed(1)}%
                                      </span>
                                    </div>
                                  )}
                                </div>
                              </div>

                              {/* GenAI Explanation */}
                              {caseItem.validation_result.ai_explanation && (
                                <div style={{
                                  backgroundColor: '#f0f9ff',
                                  border: '1px solid #bfdbfe',
                                  borderRadius: '0.5rem',
                                  padding: '1rem',
                                  marginTop: '1rem'
                                }}>
                                  <h5 style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.5rem',
                                    color: '#1e40af',
                                    fontSize: '1rem',
                                    fontWeight: 600,
                                    marginBottom: '0.5rem'
                                  }}>
                                    <AlertCircle size={18} />
                                    AI Analysis Explanation
                                  </h5>
                                  <p style={{fontSize: '0.875rem', color: '#374151', lineHeight: '1.5'}}>
                                    {caseItem.validation_result.ai_explanation}
                                  </p>
                                </div>
                              )}

                              {/* Anomalies Detected */}
                              {caseItem.validation_result.anomalies && caseItem.validation_result.anomalies.length > 0 && (
                                <div className="anomalies-section">
                                  <h5>
                                    <AlertTriangle size={18} />
                                    Anomalies Detected ({caseItem.validation_result.anomalies.length})
                                  </h5>
                                  <div className="anomalies-list">
                                    {caseItem.validation_result.anomalies.map((anomaly, idx) => (
                                      <div key={idx} className={`anomaly-item severity-${anomaly.severity || 'medium'}`}>
                                        <div className="anomaly-header">
                                          <span className="anomaly-type">{anomaly.type || 'Unknown'}</span>
                                          <span className={`anomaly-severity ${anomaly.severity || 'medium'}`}>
                                            {anomaly.severity || 'MEDIUM'}
                                          </span>
                                        </div>
                                        {anomaly.field && (
                                          <div className="anomaly-field">Field: {anomaly.field}</div>
                                        )}
                                        <div className="anomaly-description">
                                          {anomaly.description || anomaly.message || 'No description available'}
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {/* Recommendations */}
                              {caseItem.validation_result.recommendations && caseItem.validation_result.recommendations.length > 0 && (
                                <div className="recommendations-section">
                                  <h5>AI Recommendations</h5>
                                  <ul className="recommendations-list">
                                    {caseItem.validation_result.recommendations.map((rec, idx) => (
                                      <li key={idx}>{rec}</li>
                                    ))}
                                  </ul>
                                </div>
                              )}

                              {/* Validation Scores Breakdown */}
                              {caseItem.validation_result.field_validations && (
                                <div className="scores-breakdown">
                                  <h5>Field Validation Scores</h5>
                                  <div className="scores-grid">
                                    {Object.entries(caseItem.validation_result.field_validations).map(([field, score]) => (
                                      <div key={field} className="score-item">
                                        <div className="score-label">{field.replace(/_/g, ' ')}</div>
                                        <div className="score-bar">
                                          <div 
                                            className="score-fill" 
                                            style={{
                                              width: `${score * 100}%`,
                                              backgroundColor: score > 0.8 ? '#059669' : score > 0.6 ? '#d97706' : '#dc2626'
                                            }}
                                          />
                                        </div>
                                        <div className="score-value">{(score * 100).toFixed(0)}%</div>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>
                        )}

                        {/* Document Reupload Section for RETURNED_TO_MAKER cases */}
                        {currentUser?.role === 'MAKER' && caseItem.status === 'RETURNED_TO_MAKER' && caseItem.created_by === currentUser.id && (
                          <div className="details-section">
                            <h4 style={{color: '#f59e0b'}}>
                              <Upload size={18} />
                              Reupload Documents
                            </h4>
                            <div style={{
                              backgroundColor: '#fffbeb',
                              border: '1px solid: #fcd34d',
                              borderRadius: '0.5rem',
                              padding: '1rem',
                              marginBottom: '1rem'
                            }}>
                              <p style={{color: '#92400e', marginBottom: '0.5rem'}}>
                                <strong>Checker's Feedback:</strong> {caseItem.return_reason}
                              </p>
                              <p style={{fontSize: '0.875rem', color: '#78350f'}}>
                                Please fix the issues mentioned above and reupload the necessary documents.
                              </p>
                            </div>
                            
                            <div className="documents-grid">
                              {['pan', 'aadhaar', 'passport'].map(docType => (
                                <div key={docType} className="document-upload">
                                  <label className="upload-label">{docType.toUpperCase()}</label>
                                  <div className="upload-area">
                                    <input
                                      type="file"
                                      onChange={(e) => handleFileUpload(docType, e, caseItem.id)}
                                      id={`reupload-${docType}-${caseItem.id}`}
                                      accept=".pdf,.jpg,.jpeg,.png"
                                      style={{display: 'none'}}
                                    />
                                    <label htmlFor={`reupload-${docType}-${caseItem.id}`} className="upload-button">
                                      <Upload size={32} />
                                      <span>
                                        {caseItem.documents && caseItem.documents[docType] 
                                          ? `Current: ${caseItem.documents[docType]}` 
                                          : `Upload ${docType.toUpperCase()}`}
                                      </span>
                                      {uploadProgress[docType] === 'uploading' && (
                                        <div style={{marginTop: '0.5rem', fontSize: '0.75rem', color: '#d97706'}}>
                                          ⏳ Uploading...
                                        </div>
                                      )}
                                      {uploadProgress[docType] === 'success' && (
                                        <div className="upload-success">✓ Reuploaded</div>
                                      )}
                                      {uploadProgress[docType] === 'error' && (
                                        <div style={{marginTop: '0.5rem', fontSize: '0.75rem', color: '#dc2626'}}>
                                          ✗ Error
                                        </div>
                                      )}
                                    </label>
                                  </div>
                                </div>
                              ))}
                            </div>
                            
                            <p style={{fontSize: '0.875rem', color: '#6b7280', marginTop: '1rem'}}>
                              After reuploading the necessary documents, click "Resubmit" above to send the case back to the checker.
                            </p>
                          </div>
                        )}

                        {/* OCR Extracted Data Section */}
                        {caseItem.ocr_results && Object.keys(caseItem.ocr_results).length > 0 && (
                          <div className="details-section">
                            <h4>
                              <FileCheck size={18} />
                              AI-Extracted Data from Documents
                            </h4>
                            {renderOCRResults(caseItem.ocr_results)}
                          </div>
                        )}

                        {/* Audit Trail */}
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