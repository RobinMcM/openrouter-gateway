import logging
import re
from pathlib import Path
from typing import List
from collections import deque

# Configuration
LOG_FILE = "/tmp/openrouter-gateway.log"
LOG_FORMAT = "%(asctime)s %(levelname)s %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
MAX_ERROR_HEAD = 2048  # First N chars to capture
MAX_ERROR_TAIL = 8192  # Last N chars to capture
MAX_LOG_LINE_LENGTH = 2000

# Configure logger
logger = logging.getLogger("openrouter-gateway")
logger.setLevel(logging.INFO)

# File handler
file_handler = logging.FileHandler(LOG_FILE, mode='a')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
formatter.converter = lambda *args: __import__('time').gmtime(*args)  # Use UTC
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


def sanitize_text(text: str) -> str:
    """
    Remove sensitive data from text.
    - Redact API keys, tokens, secrets, passwords
    - Redact signed URLs
    - Redact Authorization headers
    Does NOT truncate - that's handled separately by format_error
    """
    # Redact X-Internal-API-Key header
    text = re.sub(r'(X-Internal-API-Key:\s*)[^\s]+', r'\1[REDACTED]', text, flags=re.IGNORECASE)
    
    # Redact Authorization header
    text = re.sub(r'(Authorization:\s*)[^\s]+', r'\1[REDACTED]', text, flags=re.IGNORECASE)
    
    # Redact key=value, token=value, secret=value, password=value patterns
    text = re.sub(
        r'\b(key|token|secret|password|apikey|api_key|authorization)=([^\s&]+)',
        r'\1=[REDACTED]',
        text,
        flags=re.IGNORECASE
    )
    
    # Redact JSON-style keys in request/response bodies
    text = re.sub(
        r'(["\'])(api_key|apikey|token|secret|password|authorization)(["\'])\s*:\s*(["\'])([^"\']+)\4',
        r'\1\2\3: \4[REDACTED]\4',
        text,
        flags=re.IGNORECASE
    )
    
    # Redact signed URLs (query params with signature/key/token)
    text = re.sub(
        r'\?(.*?)(signature|key|token|sig)=([^&\s]+)',
        r'?[SIGNED_URL_REDACTED]',
        text,
        flags=re.IGNORECASE
    )
    
    return text


def sanitize_log_line(line: str) -> str:
    """
    Remove sensitive data from a single log line.
    Used for /api/logs endpoint only.
    """
    return sanitize_text(line)


def format_error(error: str) -> str:
    """
    Format error for logging: sanitize first, then slice to head+tail if needed.
    
    Args:
        error: Raw error string
        
    Returns:
        Sanitized and formatted string with head and tail sections if truncated
    """
    if not error:
        return ""
    
    # STEP 1: Sanitize the full error FIRST (before slicing)
    error = sanitize_text(error)
    
    total_length = len(error)
    
    # STEP 2: If short enough, return full sanitized content
    if total_length <= (MAX_ERROR_HEAD + MAX_ERROR_TAIL):
        return error
    
    # STEP 3: Extract head and tail from sanitized content
    error_head = error[:MAX_ERROR_HEAD]
    error_tail = error[-MAX_ERROR_TAIL:]
    
    # Calculate how many chars were omitted
    omitted = total_length - MAX_ERROR_HEAD - MAX_ERROR_TAIL
    
    # Format with clear section markers
    return (
        f"[ERROR_HEAD]\n"
        f"{error_head}\n\n"
        f"[... {omitted} characters omitted ...]\n\n"
        f"[ERROR_TAIL]\n"
        f"{error_tail}"
    )


def log_request(endpoint: str, job_id: str):
    """Log incoming request"""
    logger.info(f"job={job_id} endpoint={endpoint} status=started")


def log_success(job_id: str, details: str = ""):
    """Log successful completion"""
    if details:
        logger.info(f"job={job_id} status=success details={details}")
    else:
        logger.info(f"job={job_id} status=success")


def log_error(job_id: str, error_message: str):
    """Log error with sanitization and head+tail formatting"""
    # Format error: sanitize first, then head+tail if needed
    error_message = format_error(error_message)
    
    logger.error(f"job={job_id} status=error message={error_message}")


def read_last_n_lines(filepath: str, n: int) -> List[str]:
    """
    Read last N lines from log file efficiently.
    Returns empty list if file doesn't exist.
    """
    path = Path(filepath)
    
    if not path.exists():
        return []
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            # Use deque with maxlen for efficient tail reading
            return list(deque(f, maxlen=n))
    except Exception as e:
        logger.error(f"Failed to read log file: {e}")
        return []


def get_sanitized_logs(n: int = 200) -> List[str]:
    """
    Get last N lines from log file with sanitization.
    Removes sensitive data before returning.
    """
    lines = read_last_n_lines(LOG_FILE, n)
    
    # Sanitize each line
    sanitized_lines = []
    for line in lines:
        sanitized = sanitize_log_line(line.rstrip('\n'))
        sanitized_lines.append(sanitized)
    
    return sanitized_lines
