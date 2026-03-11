import { useState } from 'react'
import './FileUpload.css'

function FileUpload({ onUploadSuccess }) {
  const [uploading, setUploading] = useState(false)
  const [dragActive, setDragActive] = useState(false)

  const handleFiles = async (files) => {
    if (!files || files.length === 0) return

    setUploading(true)
    
    // Upload files one by one
    for (const file of files) {
      try {
        const formData = new FormData()
        formData.append('file', file)
        formData.append('document_name', file.name)

        const response = await fetch('http://localhost:8000/api/rag/upload', {
          method: 'POST',
          body: formData
        })

        if (response.ok) {
          const result = await response.json()
          onUploadSuccess?.(result)
        } else {
          console.error('Upload failed:', await response.text())
        }
      } catch (error) {
        console.error('Upload error:', error)
      }
    }
    
    setUploading(false)
  }

  const handleDrag = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFiles(Array.from(e.dataTransfer.files))
    }
  }

  const handleChange = (e) => {
    e.preventDefault()
    if (e.target.files && e.target.files[0]) {
      handleFiles(Array.from(e.target.files))
    }
  }

  return (
    <div className="file-upload">
      <div
        className={`upload-area ${dragActive ? 'drag-active' : ''} ${uploading ? 'uploading' : ''}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <input
          type="file"
          id="file-upload"
          multiple
          onChange={handleChange}
          accept=".txt,.pdf,.doc,.docx,.csv"
          disabled={uploading}
        />
        <label htmlFor="file-upload">
          {uploading ? (
            <div className="upload-status">
              <div className="spinner"></div>
              <span>Uploading...</span>
            </div>
          ) : (
            <div className="upload-content">
              <div className="upload-icon">📁</div>
              <div className="upload-text">
                <strong>Click to upload</strong> or drag and drop
              </div>
              <div className="upload-hint">
                Supports: TXT, PDF, DOC, DOCX, CSV
              </div>
            </div>
          )}
        </label>
      </div>
    </div>
  )
}

export default FileUpload
