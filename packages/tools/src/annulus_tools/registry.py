from __future__ import annotations

TOOL_DEFINITIONS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a UTF-8 text file relative to the workspace root.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative file path"},
                    "start_line": {
                        "type": "integer",
                        "description": "Optional 1-based start line",
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "Optional 1-based end line (inclusive)",
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ripgrep",
            "description": "Search file contents with ripgrep (rg) under the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Regex or literal pattern"},
                    "path": {
                        "type": "string",
                        "description": "Optional relative path (file or directory)",
                        "default": ".",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum matches to return",
                        "default": 50,
                    },
                },
                "required": ["pattern"],
            },
        },
    },
]


def tool_schemas() -> list[dict]:
    return TOOL_DEFINITIONS
