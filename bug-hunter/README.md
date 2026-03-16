# 🐛 AI Bug Hunter

A full-stack multi-agent AI system for detecting bugs in code files, CSV files, and screenshots.

## Architecture

```
React UI → FastAPI Backend → MCP Server → Agent Orchestrator
                                              ↓
                                     ┌────────┼────────┐
                                     │        │        │
                                  Parser  Static   Bug
                                  Agent   Analysis Detector
                                              │
                                     ┌────────┼────────┐
                                     │                  │
                                  LLM Ensemble      RAG Agent
                                  (3 providers)     (Pinecone)
```

## Features

- **Multi-file support**: `.py`, `.js`, `.ts`, `.csv`, `.png`, `.jpg`
- **5 Agents**: Parser, Static Analysis, Bug Detector, LLM Ensemble, RAG
- **Pattern detection**: Mutable defaults, hardcoded secrets, loose equality, etc.
- **LLM Ensemble**: OpenRouter + Gemini + Groq with majority voting
- **RAG Memory**: Pinecone vector DB for historical bug retrieval
- **OCR**: Extract code from screenshots using Tesseract
- **CSV Analysis**: Missing values, type mismatches, outliers, duplicates

## Quick Start

### Backend

```bash
cd bug-hunter/backend
pip install -r requirements.txt
cp .env.example .env    # Edit with your API keys
python -m uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd bug-hunter/frontend
npm install
npm start
```

Open `http://localhost:3000` in your browser.

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | Optional | OpenRouter LLM access |
| `GEMINI_API_KEY` | Optional | Google Gemini access |
| `GROQ_API_KEY` | Optional | Groq LLM access |
| `PINECONE_API_KEY` | Optional | Pinecone vector DB |

> **Note**: The system works without API keys. Static analysis and pattern detection still function. LLM ensemble and RAG return graceful fallback results.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React, Monaco Editor, React Dropzone |
| Backend | Python, FastAPI |
| Static Analysis | pylint, eslint |
| OCR | Tesseract (pytesseract) |
| LLMs | OpenRouter, Gemini, Groq |
| Vector DB | Pinecone |
| Embeddings | sentence-transformers |
| Isolation | MCP Server |
