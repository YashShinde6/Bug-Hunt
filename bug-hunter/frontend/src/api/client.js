import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

const client = axios.create({
  baseURL: API_BASE,
  timeout: 120000, // 2 minutes for LLM calls
});

export async function uploadFile(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await client.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

export async function analyzeFile(filePath, fileContent, language) {
  const response = await client.post('/analyze', {
    file_path: filePath,
    file_content: fileContent,
    language: language,
  });
  return response.data;
}

export async function getHistory() {
  const response = await client.get('/history');
  return response.data;
}

export default client;
