import { useState } from 'react'
import './App.css'
import FileUpload from './FileUpload.jsx'

function App() {
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [uploadedFiles, setUploadedFiles] = useState([])

  const handleUploadSuccess = (result) => {
    setUploadedFiles(prev => [...prev, result])
    setMessages(prev => [...prev, {
      type: 'system',
      content: `✅ Uploaded: ${result.document_name} (${result.chunks_created} chunks)`
    }])
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
        chunks: data.chunks_used || 0
      }
      setMessages(prev => [...prev, aiMessage])
    } catch (error) {
      setMessages(prev => [...prev, { type: 'error', content: 'Error connecting to API' }])
    }

    setQuestion('')
    setLoading(false)
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
      </div>
    </div>
  )
}

export default App