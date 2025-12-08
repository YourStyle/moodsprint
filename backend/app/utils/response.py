"""API response helpers."""

from typing import Any
from flask import jsonify


def success_response(
    data: Any = None, message: str | None = None, status_code: int = 200
):
    """Create a success response."""
    response = {"success": True}

    if data is not None:
        response["data"] = data

    if message is not None:
        response["message"] = message

    return jsonify(response), status_code


def error_response(
    code: str, message: str, details: dict | None = None, status_code: int = 400
):
    """Create an error response."""
    response = {"success": False, "error": {"code": code, "message": message}}

    if details is not None:
        response["error"]["details"] = details

    return jsonify(response), status_code


# Common error responses
def unauthorized(message: str = "Unauthorized"):
    """401 Unauthorized response."""
    return error_response("UNAUTHORIZED", message, status_code=401)


def forbidden(message: str = "Access denied"):
    """403 Forbidden response."""
    return error_response("FORBIDDEN", message, status_code=403)


def not_found(message: str = "Resource not found"):
    """404 Not Found response."""
    return error_response("NOT_FOUND", message, status_code=404)


def validation_error(details: dict):
    """400 Validation Error response."""
    return error_response(
        "VALIDATION_ERROR", "Invalid input data", details, status_code=400
    )


def conflict(message: str = "Resource conflict"):
    """409 Conflict response."""
    return error_response("CONFLICT", message, status_code=409)


def server_error(message: str = "Internal server error"):
    """500 Internal Server Error response."""
    return error_response("SERVER_ERROR", message, status_code=500)
