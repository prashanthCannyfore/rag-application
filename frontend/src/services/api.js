import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api/rag';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const uploadDocument = async (file, documentName) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('document_name', documentName || file.name);
  
  const response = await api.post('/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  
  return response.data;
};

export const searchRAG = async (question, documentId = null, options = {}) => {
  const payload = {
    question,
    document_id: documentId,
    max_chunks: options.maxChunks || 5,
    search_type: options.searchType || 'hybrid',
    use_rerank: options.useRerank !== false,
    use_summarize: options.useSummarize || false,
  };
  
  const response = await api.post('/search', payload);
  return response.data;
};

export const listDocuments = async () => {
  const response = await api.get('/documents');
  return response.data;
};

export const downloadResume = (documentId) => {
  return `${API_BASE_URL}/download/resume/${documentId}`;
};

export const deleteDocument = async (documentId) => {
  const response = await api.delete(`/documents/${documentId}`);
  return response.data;
};

export default api;
