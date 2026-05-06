import React, { useState, useCallback, useEffect, useRef } from 'react';
import '../App.css';
import Header from './Header';
import FileUploader from './FileUploader';
import CodeEditor from './CodeEditor';
import AnalyzeButton from './AnalyzeButton';
import ResultPanel from './ResultPanel';
import { uploadFile, analyzeFile } from '../api/client';
import { auth } from '../firebase';
import { signOut } from 'firebase/auth';

export default function MainApp() {
  const [uploadedFile, setUploadedFile] = useState(null);
  const [code, setCode] = useState('');
  const [language, setLanguage] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [stage, setStage] = useState(0);
  const stageInterval = useRef(null);

  // Clean up interval on unmount
  useEffect(() => {
    return () => {
      if (stageInterval.current) clearInterval(stageInterval.current);
    };
  }, []);

  const handleFileSelect = useCallback(async (file) => {
    setError('');
    setResults(null);

    try {
      const response = await uploadFile(file);
      setUploadedFile(response);
      setLanguage(response.language);

      if (response.content) {
        setCode(response.content);
      } else if (response.language === 'image') {
        setCode('// Image uploaded — click "Analyze" to extract code via OCR');
      } else {
        setCode('');
      }
    } catch (err) {
      const message = err.response?.data?.detail || err.message || 'Upload failed';
      setError(message);
    }
  }, []);

  const handleAnalyze = useCallback(async () => {
    if (!uploadedFile) return;

    setLoading(true);
    setError('');
    setStage(0);
    setResults(null);

    // Simulate pipeline stage progression
    stageInterval.current = setInterval(() => {
      setStage((prev) => (prev < 5 ? prev + 1 : prev));
    }, 1500);

    try {
      const response = await analyzeFile(
        uploadedFile.file_path,
        uploadedFile.content,
        uploadedFile.language
      );
      setResults(response);
      setStage(5);

      // If OCR extracted code from an image, update the editor
      if (response.extracted_code) {
        setCode(response.extracted_code);
        if (response.detected_language) {
          setLanguage(response.detected_language);
        }
      }
    } catch (err) {
      const message = err.response?.data?.detail || err.message || 'Analysis failed';
      setError(message);
    } finally {
      setLoading(false);
      if (stageInterval.current) clearInterval(stageInterval.current);
    }
  }, [uploadedFile, code]);

  const handleClear = useCallback(() => {
    setUploadedFile(null);
    setCode('');
    setLanguage('');
    setResults(null);
    setError('');
  }, []);

  const handleLogout = () => {
    signOut(auth);
  };

  // Get bug line numbers for editor highlighting
  const bugLines = results?.bugs
    ?.map((b) => b.line_number)
    .filter((l) => l > 0) || [];

  return (
    <div className="app">
      <Header />
      <div style={{ position: 'absolute', top: '1rem', right: '1rem' }}>
        <button 
          onClick={handleLogout} 
          style={{ background: 'rgba(239,68,68,0.2)', border: '1px solid #ef4444', color: '#f8fafc', padding: '0.5rem 1rem', borderRadius: '8px', cursor: 'pointer' }}
        >
          Logout
        </button>
      </div>

      <main className="app-main">
        {error && (
          <div className="app-error">
            ⚠️ {error}
            <button className="app-error-close" onClick={() => setError('')}>✕</button>
          </div>
        )}

        <div className="app-grid">
          <div className="app-left">
            <FileUploader
              onFileSelect={handleFileSelect}
              uploadedFile={uploadedFile}
              onClear={handleClear}
            />
            <CodeEditor
              code={code}
              language={language}
              bugLines={bugLines}
            />
            <AnalyzeButton
              onClick={handleAnalyze}
              loading={loading}
              disabled={!uploadedFile}
              stage={stage}
            />
          </div>
          <div className="app-right">
            <ResultPanel results={results} />
          </div>
        </div>
      </main>
    </div>
  );
}
