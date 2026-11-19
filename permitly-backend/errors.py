"""
errors.py
=========
Task B7: every error leaves the API as clean JSON, never as a stack trace:

  {"error": {"code": "rate_limited", "message": "...", "request_id": "ab12cd34"}}
"""


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, headers: dict | None = None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.headers = headers or {}
