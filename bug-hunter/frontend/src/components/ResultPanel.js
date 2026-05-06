import React from 'react';
import './ResultPanel.css';

const SEVERITY_ICONS = {
  critical: '🔴',
  high: '🟠',
  medium: '🟡',
  low: '🔵',
  info: '⚪',
};

export default function ResultPanel({ results }) {
  if (!results) return null;

  const { bugs, summary } = results;
  const realBugs = bugs.filter((b) => b.bug_type !== 'No Issues');
  const isClean = realBugs.length === 0;

  return (
    <div className="results-container" id="results-panel">
      <div className="results-title">
        🔎 Analysis Results
        <span className={`results-count ${isClean ? 'results-count-clean' : ''}`}>
          {isClean ? '✓ Clean' : `${realBugs.length} bug${realBugs.length !== 1 ? 's' : ''} found`}
        </span>
      </div>

      {/* Summary */}
      {summary && (
        <div className="results-summary">
          {summary.from_ocr && (
            <div className="ocr-info-card" style={{
              background: 'linear-gradient(135deg, #1e1b4b, #312e81)',
              border: '1px solid #4c1d95',
              borderRadius: '10px',
              padding: '12px 16px',
              marginBottom: '12px',
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
            }}>
              <span style={{ fontSize: '1.5rem' }}>📸</span>
              <div>
                <div style={{ fontWeight: 600, color: '#c4b5fd', fontSize: '0.9rem' }}>
                  Code Extracted via OCR
                  {summary.ocr_method && (
                    <span style={{
                      marginLeft: '8px', fontSize: '0.7rem', padding: '2px 8px',
                      background: '#4c1d95', borderRadius: '12px', color: '#a78bfa',
                    }}>
                      {summary.ocr_method === 'gemini_vision' ? '✨ Gemini Vision' : '🔤 Tesseract'}
                    </span>
                  )}
                </div>
                <div style={{ color: '#8b5cf6', fontSize: '0.8rem', marginTop: '2px' }}>
                  {summary.ocr_lines_extracted || summary.line_count || 0} lines extracted
                  {summary.file_type && summary.file_type !== 'image' && ` • Detected: ${summary.file_type}`}
                </div>
              </div>
            </div>
          )}
          <div className="results-summary-grid">
            <div className="summary-stat">
              <div className="summary-stat-value" style={{ color: 'var(--accent-red)' }}>
                {summary.total_bugs || 0}
              </div>
              <div className="summary-stat-label">Bugs Found</div>
            </div>
            {summary.line_count > 0 && (
              <div className="summary-stat">
                <div className="summary-stat-value" style={{ color: 'var(--accent-blue)' }}>
                  {summary.line_count}
                </div>
                <div className="summary-stat-label">Lines</div>
              </div>
            )}
            {summary.functions_found > 0 && (
              <div className="summary-stat">
                <div className="summary-stat-value" style={{ color: 'var(--accent-cyan)' }}>
                  {summary.functions_found}
                </div>
                <div className="summary-stat-label">Functions</div>
              </div>
            )}
            <div className="summary-stat">
              <div className="summary-stat-value" style={{ color: 'var(--accent-green)' }}>
                {summary.file_type || '—'}
              </div>
              <div className="summary-stat-label">Language</div>
            </div>
          </div>
        </div>
      )}

      {/* Bug Cards */}
      {isClean ? (
        <div className="no-bugs">
          <span className="no-bugs-icon">🎉</span>
          <div className="no-bugs-title">No bugs detected!</div>
          <div className="no-bugs-text">Your code looks clean. Great job!</div>
        </div>
      ) : (
        realBugs.map((bug, index) => (
          <BugCard key={index} bug={bug} index={index} />
        ))
      )}

      {/* Pipeline Stages */}
      {summary?.pipeline_stages && (
        <div className="pipeline-stages">
          <div className="pipeline-title">Pipeline Log</div>
          {summary.pipeline_stages.map((stage, i) => (
            <div key={i} className="pipeline-stage">
              ▸ {stage}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function BugCard({ bug, index }) {
  const severity = bug.severity || 'medium';
  const icon = SEVERITY_ICONS[severity] || '🟡';
  const historicalBugs = bug.historical_bugs || [];

  return (
    <div className="bug-card" style={{ animationDelay: `${index * 0.1}s` }}>
      <div className="bug-card-header">
        <div>
          <div className="bug-card-type">
            {icon} {bug.bug_type}
            {bug.llm_validated !== undefined && (
              <span className={`validation-badge ${bug.llm_validated ? 'validation-confirmed' : 'validation-unconfirmed'}`}>
                {bug.llm_validated ? '✓ LLM Confirmed' : '⚠ Unconfirmed'}
                {bug.validation_votes && ` (${bug.validation_votes})`}
              </span>
            )}
          </div>
          <span className={`severity-badge severity-${severity}`}>{severity}</span>
        </div>
        {bug.line_number > 0 && (
          <span className="bug-card-line">Line {bug.line_number}</span>
        )}
      </div>

      <div className="bug-card-body">
        <div className="bug-field">
          <span className="bug-field-label">Explanation</span>
          <span className="bug-field-value">{bug.explanation}</span>
        </div>

        <div className="bug-field">
          <span className="bug-field-label">Impact</span>
          <span className="bug-field-value">{bug.impact}</span>
        </div>

        {bug.suggested_fix && (
          <div className="bug-field bug-fix">
            <span className="bug-field-label">Fix</span>
            <span className="bug-field-value">{bug.suggested_fix}</span>
          </div>
        )}

        {historicalBugs.length > 0 && (
          <div className="historical-bugs">
            <span className="bug-field-label">Similar Past Bugs</span>
            {historicalBugs.map((hb, i) => (
              <div key={i} className="historical-bug">
                <div className="historical-bug-type">{hb.bug_type || 'Related Bug'}</div>
                <div>{hb.explanation || hb.fix || 'Similar issue found in history'}</div>
                {hb.similarity > 0 && (
                  <div className="historical-bug-score">
                    Similarity: {(hb.similarity * 100).toFixed(0)}%
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
