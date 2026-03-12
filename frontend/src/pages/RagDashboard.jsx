import { useState, useEffect, useRef } from 'react';
import { Upload, Send, Trash2, Download, Briefcase } from 'lucide-react';
import DocumentUpload from '../components/DocumentUpload';
import CandidateResult from '../components/CandidateResult';
import { listDocuments, searchRAG, deleteDocument } from '../services/api';

export default function RagDashboard() {
  const [documents, setDocuments] = useState([]);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [messages, setMessages] = useState([]);
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(false);
  const [input, setInput] = useState('');
  const [showUpload, setShowUpload] = useState(false);
  const [showJobSearch, setShowJobSearch] = useState(false);
  const [jobDescription, setJobDescription] = useState('');
  const [candidates, setCandidates] = useState([]);
  const [jobSearchLoading, setJobSearchLoading] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    loadDocuments();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadDocuments = async () => {
    try {
      const data = await listDocuments();
      if (data.documents) {
        setDocuments(data.documents);
      } else if (Array.isArray(data)) {
        setDocuments(data);
      }
    } catch (error) {
      console.error('Failed to load documents:', error);
    }
  };

  const handleUploadSuccess = (result) => {
    const newDoc = {
      id: result.document_id,
      name: result.document_name,
      chunks_created: result.chunks_created,
    };
    setDocuments([...documents, newDoc]);
    setShowUpload(false);
  };

  const handleDeleteDoc = async (docId) => {
    if (!confirm('Delete this document?')) return;
    try {
      await deleteDocument(docId);
      setDocuments(documents.filter(d => d.id !== docId));
      if (selectedDoc?.id === docId) {
        setSelectedDoc(null);
      }
    } catch (error) {
      console.error('Failed to delete', error);
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const question = input.trim();
    setInput('');
    
    const userMessage = { role: 'user', content: question };
    setMessages([...messages, userMessage]);
    setLoading(true);

    try {
      const response = await searchRAG(question, selectedDoc?.id);
      const aiMessage = { role: 'assistant', content: response.answer };
      setMessages(prev => [...prev, aiMessage]);
      setSources(response.sources || []);
    } catch (error) {
      const errorMessage = {
        role: 'assistant',
        content: 'Error processing your question. Please try again.',
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const downloadResume = (documentId) => {
    window.open(`http://localhost:8000/api/rag/download/resume/${documentId}`, '_blank');
  };

  const handleJobSearch = async (e) => {
    e.preventDefault();
    if (!jobDescription.trim() || jobSearchLoading) return;

    setJobSearchLoading(true);
    try {
      const formData = new FormData();
      formData.append('job_description', jobDescription);
      formData.append('max_results', 10);
      formData.append('strict_location', true);

      const response = await fetch('http://localhost:8000/api/rag/search/job', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) throw new Error('Job search failed');
      
      const data = await response.json();
      setCandidates(data.candidates || []);
      
      // Populate sources with matched resumes
      const matchedSources = (data.candidates || [])
        .filter(c => c.has_resume && c.is_pdf)
        .map((c, idx) => ({
          content: `📄 ${c.name || c.filename}`,
          document_id: c.document_id,
          similarity: (c.match_score || 0) / 100,
          chunk_index: idx,
          file_type: 'application/pdf',
          candidate_name: c.name || c.filename,
          candidate_role: c.role || 'Resume'
        }));
      
      setSources(matchedSources);
      setJobDescription('');
    } catch (error) {
      console.error('Job search error:', error);
      alert('Failed to search candidates');
    } finally {
      setJobSearchLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100%', backgroundColor: '#f5f5f5' }}>
      {/* Left Sidebar */}
      <div style={{ width: '300px', backgroundColor: '#fff', borderRight: '1px solid #e0e0e0', display: 'flex', flexDirection: 'column', overflowY: 'auto' }}>
        <div style={{ padding: '20px', borderBottom: '1px solid #e0e0e0' }}>
          <h2 style={{ fontSize: '18px', fontWeight: 'bold', margin: '0 0 5px 0' }}>Documents</h2>
          <p style={{ fontSize: '12px', color: '#666', margin: '0' }}>{documents.length} uploaded</p>
        </div>

        <div style={{ padding: '15px' }}>
          <button
            onClick={() => setShowUpload(!showUpload)}
            style={{
              width: '100%',
              padding: '10px',
              backgroundColor: '#2563eb',
              color: '#fff',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: '500',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px'
            }}
          >
            <Upload size={16} />
            Upload Files
          </button>
        </div>

        {showUpload && (
          <div style={{ padding: '15px', borderTop: '1px solid #e0e0e0', backgroundColor: '#f9f9f9' }}>
            <DocumentUpload onUploadSuccess={handleUploadSuccess} />
          </div>
        )}

        <div style={{ flex: 1, overflowY: 'auto', padding: '10px' }}>
          {documents.length === 0 ? (
            <p style={{ textAlign: 'center', color: '#999', fontSize: '13px', padding: '20px' }}>No documents yet</p>
          ) : (
            documents.map((doc) => (
              <div
                key={doc.id}
                onClick={() => setSelectedDoc(doc)}
                style={{
                  padding: '12px',
                  marginBottom: '8px',
                  backgroundColor: selectedDoc?.id === doc.id ? '#dbeafe' : '#fff',
                  border: selectedDoc?.id === doc.id ? '1px solid #3b82f6' : '1px solid #e0e0e0',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}
              >
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{ fontSize: '13px', fontWeight: '500', margin: '0 0 4px 0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{doc.name}</p>
                  <p style={{ fontSize: '11px', color: '#666', margin: '0' }}>{doc.chunks_created || 0} chunks</p>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteDoc(doc.id);
                  }}
                  style={{
                    padding: '4px',
                    backgroundColor: 'transparent',
                    border: 'none',
                    cursor: 'pointer',
                    color: '#dc2626'
                  }}
                >
                  <Trash2 size={16} />
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Center - Chat or Job Search */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', backgroundColor: '#fff' }}>
        {/* Tab Buttons */}
        <div style={{
          display: 'flex',
          gap: '0',
          borderBottom: '1px solid #e0e0e0',
          backgroundColor: '#f9f9f9',
          padding: '0'
        }}>
          <button
            onClick={() => { setShowJobSearch(false); setCandidates([]); setSources([]); }}
            style={{
              flex: 1,
              padding: '12px 16px',
              backgroundColor: !showJobSearch ? '#fff' : '#f9f9f9',
              border: 'none',
              borderBottom: !showJobSearch ? '2px solid #2563eb' : 'none',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: '500',
              color: !showJobSearch ? '#2563eb' : '#666'
            }}
          >
            💬 Chat
          </button>
          <button
            onClick={() => { setShowJobSearch(true); setMessages([]); setSources([]); }}
            style={{
              flex: 1,
              padding: '12px 16px',
              backgroundColor: showJobSearch ? '#fff' : '#f9f9f9',
              border: 'none',
              borderBottom: showJobSearch ? '2px solid #2563eb' : 'none',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: '500',
              color: showJobSearch ? '#2563eb' : '#666'
            }}
          >
            <Briefcase size={14} style={{ display: 'inline', marginRight: '6px' }} />
            Job Search
          </button>
        </div>

        {/* Chat View */}
        {!showJobSearch && (
          <div style={{ flex: 1, overflowY: 'auto', padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {messages.length === 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', textAlign: 'center' }}>
              <div style={{ fontSize: '48px', marginBottom: '16px' }}>💬</div>
              <h2 style={{ fontSize: '24px', fontWeight: 'bold', margin: '0 0 8px 0' }}>Start a conversation</h2>
              <p style={{ fontSize: '14px', color: '#666', margin: '0', maxWidth: '400px' }}>
                Upload documents and ask questions to get AI-powered answers
              </p>
            </div>
          ) : (
            <>
              {messages.map((msg, index) => (
                <div key={index} style={{ display: 'flex', gap: '12px', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
                  {msg.role === 'assistant' && (
                    <div style={{ width: '32px', height: '32px', borderRadius: '50%', backgroundColor: '#2563eb', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: '16px', flexShrink: 0 }}>🤖</div>
                  )}
                  <div style={{
                    maxWidth: '70%',
                    padding: '12px 16px',
                    borderRadius: '8px',
                    backgroundColor: msg.role === 'user' ? '#2563eb' : '#e5e7eb',
                    color: msg.role === 'user' ? '#fff' : '#000',
                    fontSize: '14px',
                    lineHeight: '1.5',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word'
                  }}>
                    {msg.content}
                  </div>
                  {msg.role === 'user' && (
                    <div style={{ width: '32px', height: '32px', borderRadius: '50%', backgroundColor: '#d1d5db', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#374151', fontSize: '16px', flexShrink: 0 }}>👤</div>
                  )}
                </div>
              ))}
              {loading && (
                <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                  <div style={{ width: '32px', height: '32px', borderRadius: '50%', backgroundColor: '#2563eb', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: '16px' }}>🤖</div>
                  <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
                    <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#999', animation: 'bounce 1.4s infinite' }}></div>
                    <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#999', animation: 'bounce 1.4s infinite 0.2s' }}></div>
                    <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#999', animation: 'bounce 1.4s infinite 0.4s' }}></div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </>
          )}
          </div>
        )}

        {/* Input */}
        {!showJobSearch && (
        <div style={{ padding: '20px', borderTop: '1px solid #e0e0e0', backgroundColor: '#fff' }}>
          <form onSubmit={handleSendMessage} style={{ display: 'flex', gap: '12px' }}>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a question..."
              disabled={loading}
              style={{
                flex: 1,
                padding: '12px 16px',
                border: '1px solid #d1d5db',
                borderRadius: '6px',
                fontSize: '14px',
                fontFamily: 'inherit',
                outline: 'none',
                opacity: loading ? 0.5 : 1
              }}
              onFocus={(e) => e.target.style.borderColor = '#2563eb'}
              onBlur={(e) => e.target.style.borderColor = '#d1d5db'}
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              style={{
                padding: '12px 24px',
                backgroundColor: '#2563eb',
                color: '#fff',
                border: 'none',
                borderRadius: '6px',
                cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
                fontSize: '14px',
                fontWeight: '500',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                opacity: loading || !input.trim() ? 0.5 : 1
              }}
            >
              <Send size={16} />
              Send
            </button>
          </form>
        </div>
        )}

        {/* Job Search View */}
        {showJobSearch && (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          {/* Results */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '20px' }}>
            {candidates.length === 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', textAlign: 'center' }}>
                <div style={{ fontSize: '48px', marginBottom: '16px' }}>🔍</div>
                <h2 style={{ fontSize: '24px', fontWeight: 'bold', margin: '0 0 8px 0' }}>Find Candidates</h2>
                <p style={{ fontSize: '14px', color: '#666', margin: '0', maxWidth: '400px' }}>
                  Enter a job description to search for matching candidates from uploaded resumes and CSV data
                </p>
              </div>
            ) : (
              <div>
                <h3 style={{ fontSize: '16px', fontWeight: '600', margin: '0 0 16px 0', color: '#1f2937' }}>
                  Found {candidates.length} matching candidate{candidates.length !== 1 ? 's' : ''}
                </h3>
                {candidates.map((candidate, index) => (
                  <CandidateResult
                    key={index}
                    candidate={candidate}
                    onDownload={downloadResume}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Job Search Input */}
          <div style={{ padding: '20px', borderTop: '1px solid #e0e0e0', backgroundColor: '#fff' }}>
            <form onSubmit={handleJobSearch} style={{ display: 'flex', gap: '12px' }}>
              <textarea
                value={jobDescription}
                onChange={(e) => setJobDescription(e.target.value)}
                placeholder="Paste job description here..."
                disabled={jobSearchLoading}
                style={{
                  flex: 1,
                  padding: '12px 16px',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontSize: '14px',
                  fontFamily: 'inherit',
                  outline: 'none',
                  opacity: jobSearchLoading ? 0.5 : 1,
                  minHeight: '80px',
                  resize: 'vertical'
                }}
                onFocus={(e) => e.target.style.borderColor = '#2563eb'}
                onBlur={(e) => e.target.style.borderColor = '#d1d5db'}
              />
              <button
                type="submit"
                disabled={jobSearchLoading || !jobDescription.trim()}
                style={{
                  padding: '12px 24px',
                  backgroundColor: '#2563eb',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: jobSearchLoading || !jobDescription.trim() ? 'not-allowed' : 'pointer',
                  fontSize: '14px',
                  fontWeight: '500',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  opacity: jobSearchLoading || !jobDescription.trim() ? 0.5 : 1,
                  height: 'fit-content'
                }}
              >
                <Briefcase size={16} />
                Search
              </button>
            </form>
          </div>
        </div>
        )}

      </div>

      {/* Right Sidebar - Sources */}
      <div style={{ width: '350px', backgroundColor: '#f9f9f9', borderLeft: '1px solid #e0e0e0', display: 'flex', flexDirection: 'column', overflowY: 'auto' }}>
        <div style={{ padding: '20px', borderBottom: '1px solid #e0e0e0', backgroundColor: '#fff' }}>
          <h2 style={{ fontSize: '18px', fontWeight: 'bold', margin: '0 0 5px 0' }}>
            {showJobSearch ? 'Matched Resumes' : 'Sources'}
          </h2>
          <p style={{ fontSize: '12px', color: '#666', margin: '0' }}>
            {showJobSearch ? `${sources.length} resume${sources.length !== 1 ? 's' : ''}` : `${sources.length} relevant chunks`}
          </p>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: '15px' }}>
          {sources.length === 0 ? (
            <p style={{ textAlign: 'center', color: '#999', fontSize: '13px', padding: '20px' }}>No sources yet</p>
          ) : (
            sources.map((source, index) => {
              const similarity = Math.round((source.similarity || 0) * 100);
              return (
                <div key={index} style={{ marginBottom: '12px', padding: '12px', backgroundColor: '#fff', border: '1px solid #e0e0e0', borderRadius: '6px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <div>
                      <p style={{ fontSize: '12px', fontWeight: '600', margin: '0 0 2px 0', color: '#1f2937' }}>
                        {source.candidate_name || `Source ${index + 1}`}
                      </p>
                      {source.candidate_role && (
                        <p style={{ fontSize: '11px', margin: '0', color: '#6b7280' }}>
                          {source.candidate_role}
                        </p>
                      )}
                    </div>
                    <span style={{
                      fontSize: '11px',
                      fontWeight: '500',
                      padding: '2px 8px',
                      borderRadius: '4px',
                      backgroundColor: similarity >= 80 ? '#dcfce7' : similarity >= 60 ? '#fef3c7' : '#f3f4f6',
                      color: similarity >= 80 ? '#166534' : similarity >= 60 ? '#92400e' : '#374151'
                    }}>
                      {similarity}%
                    </span>
                  </div>
                  <p style={{ fontSize: '12px', color: '#333', margin: '0 0 8px 0', lineHeight: '1.4', maxHeight: '60px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {source.content}
                  </p>
                  {source.file_type !== 'text/csv' && (
                    <button
                      onClick={() => downloadResume(source.document_id)}
                      style={{
                        width: '100%',
                        padding: '6px 12px',
                        backgroundColor: '#dbeafe',
                        color: '#2563eb',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '12px',
                        fontWeight: '500',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '6px'
                      }}
                    >
                      <Download size={14} />
                      Download
                    </button>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>

      <style>{`
        @keyframes bounce {
          0%, 80%, 100% { opacity: 0.5; }
          40% { opacity: 1; }
        }
      `}</style>
    </div>
  );
}
