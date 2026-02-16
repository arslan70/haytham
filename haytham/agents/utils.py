"""
Shared utilities for Haytham agents.

This module provides common functionality used across all agents including:
- Safe file reading with security checks
- Directory scanning with exclusion patterns
- Agent response parsing
- Performance timing decorators
"""

import logging
import time
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any

# Configure logging
logger = logging.getLogger(__name__)

# Security configuration
ALLOWED_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",  # Code files
    ".md",
    ".txt",
    ".rst",  # Documentation
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",  # Configuration
    ".html",
    ".css",
    ".scss",
    ".sass",  # Web assets
    ".sh",
    ".bash",  # Scripts
    ".sql",  # Database
    ".dockerfile",
    ".dockerignore",  # Docker
    ".gitignore",
    ".gitattributes",  # Git
}

BLOCKED_FILES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    ".pem",
    ".key",
    ".crt",
    ".p12",
    ".pfx",
    "credentials",
    "secrets",
    "secret",
    "private_key",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "password",
    "passwd",
    "token",
    "api_key",
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB per file

# Default exclusion patterns for directory scanning
DEFAULT_EXCLUDE_PATTERNS = {
    "__pycache__",
    ".git",
    ".svn",
    ".hg",
    "node_modules",
    ".venv",
    "venv",
    "env",
    ".env",
    "dist",
    "build",
    ".next",
    ".nuxt",
    "coverage",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".DS_Store",
    "Thumbs.db",
}


def read_file_safely(file_path: str, max_size: int = MAX_FILE_SIZE) -> str:
    """
    Safely read file contents with security checks and error handling.

    Security features:
    - Validates file extension against allowlist
    - Checks for blocked filenames (secrets, credentials, etc.)
    - Enforces file size limits
    - Prevents path traversal attacks
    - Read-only access

    Args:
        file_path: Path to the file to read
        max_size: Maximum file size in bytes (default: 10MB)

    Returns:
        File contents as string

    Raises:
        FileNotFoundError: If file doesn't exist
        PermissionError: If file is blocked for security reasons
        ValueError: If file is too large or has invalid extension
    """
    try:
        # Convert to Path object and resolve to absolute path
        path = Path(file_path).resolve()

        # Check if file exists
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not path.is_file():
            raise ValueError(f"Not a file: {file_path}")

        # Security check: validate extension
        extension = path.suffix.lower()
        if extension and extension not in ALLOWED_EXTENSIONS:
            raise PermissionError(
                f"File extension '{extension}' not allowed for security reasons. "
                f"Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )

        # Security check: blocked filenames
        filename_lower = path.name.lower()
        for blocked in BLOCKED_FILES:
            if blocked in filename_lower:
                raise PermissionError(
                    f"File '{path.name}' is blocked for security reasons (contains '{blocked}')"
                )

        # Security check: file size
        file_size = path.stat().st_size
        if file_size > max_size:
            raise ValueError(f"File too large: {file_size} bytes (max: {max_size} bytes)")

        # Read file contents
        with open(path, encoding="utf-8", errors="ignore") as f:
            content = f.read()

        logger.debug(f"Successfully read file: {file_path} ({file_size} bytes)")
        return content

    except UnicodeDecodeError:
        # Try reading as binary if UTF-8 fails
        logger.warning(f"UTF-8 decode failed for {file_path}, attempting binary read")
        with open(path, "rb") as f:
            content = f.read()
        return f"[Binary file: {len(content)} bytes]"

    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        raise


def scan_directory(
    path: str, exclude: list[str] = None, max_depth: int = 10, include_hidden: bool = False
) -> dict[str, Any]:
    """
    Scan directory structure with exclusion patterns.

    Args:
        path: Root directory path to scan
        exclude: Additional patterns to exclude (merged with defaults)
        max_depth: Maximum directory depth to scan (default: 10)
        include_hidden: Whether to include hidden files/directories (default: False)

    Returns:
        Dictionary containing:
        - 'path': Root path
        - 'files': List of file paths (relative to root)
        - 'directories': List of directory paths (relative to root)
        - 'structure': Nested dictionary representing directory tree
        - 'stats': Statistics (file count, directory count, total size)

    Raises:
        FileNotFoundError: If directory doesn't exist
        PermissionError: If directory is not accessible
    """
    try:
        # Convert to Path object and resolve
        root_path = Path(path).resolve()

        if not root_path.exists():
            raise FileNotFoundError(f"Directory not found: {path}")

        if not root_path.is_dir():
            raise ValueError(f"Not a directory: {path}")

        # Merge exclusion patterns
        exclude_patterns = DEFAULT_EXCLUDE_PATTERNS.copy()
        if exclude:
            exclude_patterns.update(exclude)

        # Initialize result structure
        result = {
            "path": str(root_path),
            "files": [],
            "directories": [],
            "structure": {},
            "stats": {
                "file_count": 0,
                "directory_count": 0,
                "total_size": 0,
                "scanned_files": 0,
                "skipped_files": 0,
            },
        }

        def should_exclude(item_path: Path) -> bool:
            """Check if path should be excluded."""
            # Check if hidden (starts with .)
            if not include_hidden and item_path.name.startswith("."):
                return True

            # Check against exclusion patterns
            for pattern in exclude_patterns:
                if pattern in item_path.parts or item_path.name == pattern:
                    return True

            return False

        def scan_recursive(current_path: Path, depth: int = 0) -> dict[str, Any]:
            """Recursively scan directory."""
            if depth > max_depth:
                logger.warning(f"Max depth {max_depth} reached at {current_path}")
                return {}

            structure = {}

            try:
                items = sorted(current_path.iterdir())
            except PermissionError:
                logger.warning(f"Permission denied: {current_path}")
                return structure

            for item in items:
                # Skip excluded items
                if should_exclude(item):
                    result["stats"]["skipped_files"] += 1
                    continue

                relative_path = item.relative_to(root_path)

                if item.is_file():
                    # Add file to results
                    result["files"].append(str(relative_path))
                    result["stats"]["file_count"] += 1
                    result["stats"]["scanned_files"] += 1

                    # Get file size
                    try:
                        file_size = item.stat().st_size
                        result["stats"]["total_size"] += file_size
                        structure[item.name] = {
                            "type": "file",
                            "size": file_size,
                            "extension": item.suffix,
                        }
                    except Exception as e:
                        logger.warning(f"Error getting stats for {item}: {e}")
                        structure[item.name] = {"type": "file", "size": 0}

                elif item.is_dir():
                    # Add directory to results
                    result["directories"].append(str(relative_path))
                    result["stats"]["directory_count"] += 1

                    # Recursively scan subdirectory
                    structure[item.name] = {
                        "type": "directory",
                        "children": scan_recursive(item, depth + 1),
                    }

            return structure

        # Start scanning
        logger.info(f"Scanning directory: {root_path}")
        result["structure"] = scan_recursive(root_path)

        logger.info(
            f"Scan complete: {result['stats']['file_count']} files, "
            f"{result['stats']['directory_count']} directories, "
            f"{result['stats']['total_size']} bytes total"
        )

        return result

    except Exception as e:
        logger.error(f"Error scanning directory {path}: {e}")
        raise


def extract_agent_response(response: Any) -> str:
    """
    Extract text content from agent response object.

    Handles various response types from StrandsAgents framework:
    - String responses (return as-is)
    - Dict responses (extract 'content' or 'text' field)
    - Object responses (extract .content or .text attribute)
    - List responses (join elements)

    Args:
        response: Agent response object

    Returns:
        Extracted text content as string
    """
    try:
        # Handle None
        if response is None:
            return ""

        # Handle string
        if isinstance(response, str):
            return response

        # Handle dict
        if isinstance(response, dict):
            # Try common keys
            for key in ["content", "text", "message", "output", "result"]:
                if key in response:
                    value = response[key]
                    if isinstance(value, str):
                        return value
                    # Recursively extract if nested
                    return extract_agent_response(value)

            # If no known key, convert entire dict to string
            return str(response)

        # Handle list
        if isinstance(response, list):
            # Join list elements
            return "\n".join(str(item) for item in response)

        # Handle object with attributes
        if hasattr(response, "content"):
            return str(response.content)
        if hasattr(response, "text"):
            return str(response.text)
        if hasattr(response, "message"):
            return str(response.message)

        # Fallback: convert to string
        return str(response)

    except Exception as e:
        logger.error(f"Error extracting agent response: {e}")
        return str(response)


def timed(func: Callable) -> Callable:
    """
    Decorator for timing function execution and logging performance metrics.

    Logs execution time at INFO level and stores metrics for analysis.

    Usage:
        @timed
        def my_function():
            # function code
            pass

    Args:
        func: Function to time

    Returns:
        Wrapped function that logs execution time
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        # Record start time
        start_time = time.time()

        # Get function name
        func_name = func.__name__

        try:
            # Execute function
            logger.debug(f"Starting {func_name}")
            result = func(*args, **kwargs)

            # Calculate duration
            duration = time.time() - start_time

            # Log performance
            logger.info(f"{func_name} completed in {duration:.2f}s")

            # Store metric (could be sent to CloudWatch, etc.)
            _log_performance_metric(func_name, duration, success=True)

            return result

        except Exception as e:
            # Calculate duration even on failure
            duration = time.time() - start_time

            # Log error with timing
            logger.error(f"{func_name} failed after {duration:.2f}s: {e}")

            # Store metric
            _log_performance_metric(func_name, duration, success=False)

            # Re-raise exception
            raise

    return wrapper


def _log_performance_metric(function_name: str, duration: float, success: bool = True) -> None:
    """
    Log performance metric for analysis.

    In production, this could send metrics to CloudWatch, Datadog, etc.
    For now, it just logs to the standard logger.

    Args:
        function_name: Name of the function
        duration: Execution time in seconds
        success: Whether the function completed successfully
    """
    status = "SUCCESS" if success else "FAILURE"
    logger.info(f"METRIC: {function_name} | Duration: {duration:.2f}s | Status: {status}")

    # TODO: Send to CloudWatch or other monitoring service
    # Example:
    # cloudwatch.put_metric_data(
    #     Namespace='Haytham',
    #     MetricData=[{
    #         'MetricName': 'FunctionDuration',
    #         'Value': duration,
    #         'Unit': 'Seconds',
    #         'Dimensions': [
    #             {'Name': 'FunctionName', 'Value': function_name},
    #             {'Name': 'Status', 'Value': status}
    #         ]
    #     }]
    # )
