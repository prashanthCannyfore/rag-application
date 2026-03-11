import { useState } from 'react'
import './App.css'
import FileUpload from './FileUpload.jsx'

function App() {
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [uploadedFiles, setUploadedFiles] = useState([])
  const [lastSearch, setLastSearch] = useState(null)

  const handleUploadSuccess = (result) => {
    setUploadedFiles(prev => [...prev, result])
    setMessages(prev => [...prev, {
      type: 'system',
      content: `✅ Uploaded: ${result.document_name} (${result.chunks_created} chunks)`
    }])
  }

  const handleDownload = async (documentId, filename) => {
    try {
      const response = await fetch(`http://localhost:8000/api/rag/download/pdf/${documentId}`)
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      a.click()
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Download error:', error)
    }
  }

  const handleDownloadMatched = async (sources) => {
    try {
      const params = new URLSearchParams({
        sources: JSON.stringify(sources)
      })
      const response = await fetch(`http://localhost:8000/api/rag/download/matched?${params}`)
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'matched_documents.zip'
      a.click()
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Download error:', error)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!question.trim()) return

    setLoading(true)
    const userMessage = { type: 'user', content: question }
    setMessages(prev => [...prev, userMessage])

    try {
      const response = await fetch('http://localhost:8000/api/rag/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question })
      })
      
      const data = await response.json()
      const aiMessage = { 
        type: 'ai', 
        content: data.answer || 'No answer found',
        chunks: data.chunks_used || 0,
        sources: data.sources || []
      }
      setMessages(prev => [...prev, aiMessage])
      setLastSearch({ question, answer: data.answer, sources: data.sources })
    } catch (error) {
      setMessages(prev => [...prev, { type: 'error', content: 'Error connecting to API' }])
    }

    setQuestion('')
    setLoading(false)
  }

  const handleDownloadResults = async () => {
    if (!lastSearch) return
    
    const params = new URLSearchParams({
      question: lastSearch.question,
      answer: lastSearch.answer,
      sources: JSON.stringify(lastSearch.sources)
    })
    
    const response = await fetch(`http://localhost:8000/api/rag/download/results?${params}`)
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'search_results.csv'
    a.click()
    window.URL.revokeObjectURL(url)
  }

  return (
    <div className="app">
      <header>
        <h1>DataChat AI</h1>
        <p>Ask questions about your data</p>
      </header>

      <div className="chat-container">
        <FileUpload onUploadSuccess={handleUploadSuccess} />
        
        {uploadedFiles.length > 0 && (
          <div className="uploaded-files">
            <h3>Uploaded Documents ({uploadedFiles.length})</h3>
            <div className="file-list">
              {uploadedFiles.map((file, idx) => (
                <div key={idx} className="file-item">
                  <span className="file-name">{file.document_name}</span>
                  <span className="file-chunks">{file.chunks_created} chunks</span>
                  <button 
                    onClick={() => handleDownload(file.document_id, file.document_name)}
                    className="download-btn"
                  >
                    📥 Download
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
        
        <div className="messages">
          {messages.map((msg, idx) => (
            <div key={idx} className={`message ${msg.type}`}>
              <div className="content">{msg.content}</div>
              {msg.chunks && <div className="chunks">Chunks used: {msg.chunks}</div>}
            </div>
          ))}
          {loading && <div className="message ai loading">Thinking...</div>}
        </div>

        <form onSubmit={handleSubmit} className="input-form">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask a question about your data..."
            disabled={loading}
          />
          <button type="submit" disabled={loading || !question.trim()}>
            Send
          </button>
        </form>

        {lastSearch && (
          <>
            <button onClick={handleDownloadResults} className="download-btn">
              📥 Download Search Results (CSV)
            </button>
            <button onClick={() => handleDownloadMatched(lastSearch.sources)} className="download-btn">
              📥 Download Matched Documents (ZIP)
            </button>
          </>
        )}
      </div>
    </div>
  )
}

export default App
