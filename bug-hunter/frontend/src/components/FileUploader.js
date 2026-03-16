import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import './FileUploader.css';

const ACCEPTED_TYPES = {
  'text/x-python': ['.py'],
  'application/javascript': ['.js'],
  'text/typescript': ['.ts'],
  'text/csv': ['.csv'],
  'image/png': ['.png'],
  'image/jpeg': ['.jpg', '.jpeg'],
};

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

export default function FileUploader({ onFileSelect, uploadedFile, onClear }) {
  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      onFileSelect(acceptedFiles[0]);
    }
  }, [onFileSelect]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    maxFiles: 1,
    maxSize: 10 * 1024 * 1024,
  });

  return (
    <div className="uploader-container">
      <div
        {...getRootProps()}
        className={`dropzone ${isDragActive ? 'dropzone-active' : ''}`}
        id="file-dropzone"
      >
        <input {...getInputProps()} />
        <span className="dropzone-icon">
          {isDragActive ? '📂' : '🎯'}
        </span>
        <div className="dropzone-title">
          {isDragActive ? 'Drop your file here' : 'Drag & drop a file to analyze'}
        </div>
        <div className="dropzone-text">
          or click to browse your files
        </div>
        <div className="dropzone-formats">
          {['.py', '.js', '.ts', '.csv', '.png', '.jpg'].map((fmt) => (
            <span key={fmt} className="format-badge">{fmt}</span>
          ))}
        </div>
      </div>

      {uploadedFile && (
        <div className="file-info">
          <span className="file-info-icon">📄</span>
          <div>
            <div className="file-info-name">{uploadedFile.file_name}</div>
            <div className="file-info-size">
              {formatSize(uploadedFile.size)} • {uploadedFile.language}
            </div>
          </div>
          <button className="file-info-remove" onClick={onClear} title="Remove file">
            ✕
          </button>
        </div>
      )}
    </div>
  );
}
