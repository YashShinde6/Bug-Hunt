"""MCP Server — Tool isolation layer for agent execution."""
from typing import Any, Callable, Optional
import json


class MCPToolRegistry:
    """Registry of isolated tools accessible through the MCP protocol."""

    def __init__(self):
        self._tools: dict[str, dict] = {}

    def register(self, name: str, func: Callable, description: str, schema: dict):
        """Register a tool in the MCP registry."""
        self._tools[name] = {
            "name": name,
            "function": func,
            "description": description,
            "inputSchema": schema,
        }

    def list_tools(self) -> list[dict]:
        """List all registered tools."""
        return [
            {
                "name": tool["name"],
                "description": tool["description"],
                "inputSchema": tool["inputSchema"],
            }
            for tool in self._tools.values()
        ]

    async def call_tool(self, name: str, arguments: dict) -> dict:
        """Execute a tool by name with given arguments."""
        if name not in self._tools:
            return {"error": f"Tool '{name}' not found"}

        tool = self._tools[name]
        try:
            result = tool["function"](**arguments)
            # Handle async functions
            if hasattr(result, "__await__"):
                result = await result
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ── Tool Registration ──

def create_mcp_server() -> MCPToolRegistry:
    """Create and configure the MCP server with all tools."""
    from agents.parser_agent import parse_code
    from agents.static_analysis_agent import run_static_analysis
    from agents.bug_detector_agent import detect_bugs
    from agents.ensemble_agent import validate_with_ensemble
    from agents.rag_agent import retrieve_similar_bugs
    from tools.ocr_tool import extract_code_from_image
    from tools.csv_analyzer import analyze_csv

    registry = MCPToolRegistry()

    # Parser Tool
    registry.register(
        name="parser_tool",
        func=parse_code,
        description="Parse code into structured representation using AST",
        schema={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Source code to parse"},
                "language": {"type": "string", "description": "Programming language"},
            },
            "required": ["code", "language"],
        },
    )

    # Pylint Tool
    registry.register(
        name="pylint_tool",
        func=lambda file_path: run_static_analysis(file_path, "python"),
        description="Run pylint static analysis on a Python file",
        schema={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to Python file"},
            },
            "required": ["file_path"],
        },
    )

    # ESLint Tool
    registry.register(
        name="eslint_tool",
        func=lambda file_path: run_static_analysis(file_path, "javascript"),
        description="Run eslint static analysis on a JavaScript file",
        schema={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to JS file"},
            },
            "required": ["file_path"],
        },
    )

    # OCR Tool
    registry.register(
        name="ocr_tool",
        func=extract_code_from_image,
        description="Extract code from screenshot using OCR",
        schema={
            "type": "object",
            "properties": {
                "image_path": {"type": "string", "description": "Path to image file"},
            },
            "required": ["image_path"],
        },
    )

    # LLM Validator Tool
    registry.register(
        name="llm_validator_tool",
        func=validate_with_ensemble,
        description="Validate candidate bugs using LLM ensemble",
        schema={
            "type": "object",
            "properties": {
                "code": {"type": "string"},
                "candidate_bugs": {"type": "array"},
                "language": {"type": "string"},
            },
            "required": ["code", "candidate_bugs", "language"],
        },
    )

    # RAG Tool
    registry.register(
        name="rag_tool",
        func=retrieve_similar_bugs,
        description="Retrieve similar historical bugs from vector database",
        schema={
            "type": "object",
            "properties": {
                "bugs": {"type": "array"},
                "language": {"type": "string"},
            },
            "required": ["bugs", "language"],
        },
    )

    # CSV Analyzer Tool
    registry.register(
        name="csv_analyzer_tool",
        func=analyze_csv,
        description="Analyze CSV file for data quality issues",
        schema={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to CSV file"},
            },
            "required": ["file_path"],
        },
    )

    return registry


# Global MCP server instance
mcp_server = create_mcp_server()
