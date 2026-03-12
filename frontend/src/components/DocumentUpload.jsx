import { useState } from 'react';
import { Upload, X, Loader2 } from 'lucide-react';
import { uploadDocument } from '../services/api';
import { formatFileSize } from '../lib/utils';

export default function DocumentUpload({ onUploadSuccess }) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [error, setError] = useState(null);
  const [uploadResults, setUploadResults] = useState([]);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      setSelectedFiles(files);
      setError(null);
    }
  };

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files);
    if (files.length > 0) {
      setSelectedFiles(files);
      setError(null);
    }
  };

  const removeFile = (index) => {
    setSelectedFiles(selectedFiles.filter((_, i) => i !== index));
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0) return;

    setUploading(true);
    setError(null);
    setUploadResults([]);

    try {
      const results = [];
      for (const file of selectedFiles) {
        const result = await uploadDocument(file, file.name);
        results.push(result);
        onUploadSuccess(result);
      }
      setUploadResults(results);
      setSelectedFiles([]);
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-3">
      <div
        className={`relative border-2 border-dashed rounded-lg p-4 transition-all ${
          isDragging
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-300 hover:border-blue-400 bg-gray-50'
        } ${uploading && 'opacity-50 pointer-events-none'}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {selectedFiles.length === 0 ? (
          <div className="text-center">
            <Upload className="w-8 h-8 mx-auto text-gray-400 mb-2" />
            <p className="text-xs font-medium text-gray-700 mb-0.5">
              Drop files or click to browse
            </p>
            <p className="text-xs text-gray-500">
              PDF, CSV, TXT
            </p>
            <input
              type="file"
              accept=".pdf,.csv,.txt"
              onChange={handleFileSelect}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              disabled={uploading}
              multiple
            />
          </div>
        ) : (
          <div className="space-y-2">
            <div className="space-y-1 max-h-32 overflow-y-auto">
              {selectedFiles.map((file, index) => (
                <div key={index} className="flex items-center gap-2 p-2 bg-white rounded border border-gray-200">
                  <div className="w-4 h-4 text-blue-600">📄</div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-gray-900 truncate">
                      {file.name}
                    </p>
                    <p className="text-xs text-gray-500">
                      {formatFileSize(file.size)}
                    </p>
                  </div>
                  {!uploading && (
                    <button
                      onClick={() => removeFile(index)}
                      className="p-1 hover:bg-gray-100 rounded text-gray-400"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  )}
                </div>
              ))}
            </div>

            <button
              onClick={handleUpload}
              disabled={uploading}
              className="w-full py-2 px-3 rounded-lg font-medium text-sm transition-all bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {uploading ? (
                <>
                  <Loader2 className="w-3 h-3 animate-spin" />
                  Uploading...
                </>
              ) : (
                <>
                  <Upload className="w-3 h-3" />
                  Upload {selectedFiles.length} file{selectedFiles.length !== 1 ? 's' : ''}
                </>
              )}
            </button>
          </div>
        )}
      </div>

      {error && (
        <div className="p-2 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-xs text-red-600">{error}</p>
        </div>
      )}

      {uploadResults.length > 0 && (
        <div className="space-y-2">
          {uploadResults.map((result, index) => (
            <div key={index} className="p-3 bg-green-50 border border-green-200 rounded-lg">
              <div className="flex items-start gap-2">
                <div className="text-green-600 mt-0.5">✓</div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-green-900 mb-1">
                    {result.document_name}
                  </p>
                  <div className="text-xs text-green-700 space-y-0.5">
                    <p>📊 Chunks created: {result.chunks_created}</p>
                    <p>📝 Text length: {result.text_length} characters</p>
                    {result.text_preview && (
                      <p className="text-green-600 italic mt-1">
                        Preview: "{result.text_preview.substring(0, 100)}..."
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
