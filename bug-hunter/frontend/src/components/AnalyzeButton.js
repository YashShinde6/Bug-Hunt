import React from 'react';
import './AnalyzeButton.css';

const STAGES = [
  '🔍 Parsing code structure...',
  '⚡ Running static analysis...',
  '🐛 Detecting bugs...',
  '🤖 LLM ensemble validation...',
  '📚 Retrieving similar bugs...',
  '✅ Generating report...',
];

export default function AnalyzeButton({ onClick, loading, disabled, stage }) {
  return (
    <div className="analyze-btn-wrapper">
      <button
        id="analyze-button"
        className={`analyze-btn ${loading ? 'analyze-btn-loading' : ''}`}
        onClick={onClick}
        disabled={disabled || loading}
      >
        {loading ? (
          <>
            <span className="analyze-spinner"></span>
            Analyzing...
          </>
        ) : (
          <>
            🔬 Analyze for Bugs
          </>
        )}
      </button>

      {loading && (
        <div className="analyze-stages">
          {STAGES.map((s, i) => (
            <div
              key={i}
              className={`analyze-stage ${
                i < stage ? 'analyze-stage-done' : i === stage ? 'analyze-stage-active' : ''
              }`}
            >
              {i < stage ? '✓' : i === stage ? '▸' : '○'} {s}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
