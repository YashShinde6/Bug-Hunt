import React, { useState, useCallback, useEffect, useRef } from 'react';
import './App.css';
import Header from './components/Header';
import FileUploader from './components/FileUploader';
import CodeEditor from './components/CodeEditor';
import AnalyzeButton from './components/AnalyzeButton';
import ResultPanel from './components/ResultPanel';
import { uploadFile, analyzeFile } from './api/client';

export default function App() {
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

      // If OCR extracted code, update the editor
      if (response.summary?.from_ocr && response.bugs?.length > 0) {
        // Try to find OCR content in the response
        const ocrBug = response.bugs.find(b => b.bug_type !== 'OCR Error');
        if (ocrBug && !code.startsWith('//')) {
          // Code was likely extracted
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

  // Get bug line numbers for editor highlighting
  const bugLines = results?.bugs
    ?.map((b) => b.line_number)
    .filter((l) => l > 0) || [];

  return (
    <div className="app">
      <Header />

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
