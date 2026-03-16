import React, { useRef, useEffect } from 'react';
import Editor from '@monaco-editor/react';
import './CodeEditor.css';

const LANGUAGE_MAP = {
  python: 'python',
  javascript: 'javascript',
  typescript: 'typescript',
  csv: 'plaintext',
  image: 'plaintext',
  unknown: 'plaintext',
};

export default function CodeEditor({ code, language, bugLines }) {
  const editorRef = useRef(null);
  const decorationsRef = useRef([]);

  function handleEditorMount(editor) {
    editorRef.current = editor;
  }

  // Highlight bug lines when bugLines change
  useEffect(() => {
    if (!editorRef.current || !bugLines || bugLines.length === 0) return;

    const decorations = bugLines
      .filter((line) => line > 0)
      .map((line) => ({
        range: {
          startLineNumber: line,
          startColumn: 1,
          endLineNumber: line,
          endColumn: 1,
        },
        options: {
          isWholeLine: true,
          className: 'bug-line-highlight',
          glyphMarginClassName: 'bug-glyph',
          overviewRuler: {
            color: '#ef4444',
            position: 1,
          },
          minimap: {
            color: '#ef4444',
            position: 1,
          },
        },
      }));

    decorationsRef.current = editorRef.current.deltaDecorations(
      decorationsRef.current,
      decorations
    );
  }, [bugLines]);

  if (!code) {
    return (
      <div className="editor-container">
        <div className="editor-header">
          <div className="editor-tab">
            <span className="editor-tab-dot"></span>
            No file loaded
          </div>
        </div>
        <div className="editor-placeholder">
          <span className="editor-placeholder-icon">📝</span>
          Upload a file to view its contents
        </div>
      </div>
    );
  }

  const monacoLang = LANGUAGE_MAP[language] || 'plaintext';
  const lineCount = code.split('\n').length;

  return (
    <div className="editor-container">
      <div className="editor-header">
        <div className="editor-tab">
          <span className="editor-tab-dot"></span>
          Source Code
        </div>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <span className="editor-line-count">{lineCount} lines</span>
          <span className="editor-lang">{language}</span>
        </div>
      </div>
      <Editor
        height="450px"
        language={monacoLang}
        value={code}
        theme="vs-dark"
        onMount={handleEditorMount}
        options={{
          readOnly: true,
          minimap: { enabled: true },
          fontSize: 14,
          fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
          scrollBeyondLastLine: false,
          lineNumbers: 'on',
          glyphMargin: true,
          folding: true,
          wordWrap: 'on',
          renderLineHighlight: 'all',
          smoothScrolling: true,
          cursorBlinking: 'smooth',
        }}
      />
      <style>{`
        .bug-line-highlight {
          background: rgba(239, 68, 68, 0.15) !important;
          border-left: 3px solid #ef4444 !important;
        }
        .bug-glyph {
          background: #ef4444;
          border-radius: 50%;
          width: 8px !important;
          height: 8px !important;
          margin-left: 4px;
          margin-top: 6px;
        }
      `}</style>
    </div>
  );
}
