"""API Standardization & Global Exception Handling Middleware."""

import time
from flask import jsonify, request

def api_response(success=True, data=None, error=None, status=200, pagination=None):
    """
    Standardized Enterprise API Response Envelope
    {
      "success": boolean,
      "data": object | array | null,
      "error": { "code": string, "message": string } | null,
      "meta": { "timestamp": string, "version": string, "path": string, "pagination": object }
    }
    """
    payload = {
        "success": success,
        "data": data if success else None,
        "error": error if not success else None,
        "meta": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "version": "v2.5.0",
            "path": request.path
        }
    }
    if pagination:
        payload["meta"]["pagination"] = pagination
    return jsonify(payload), status


def register_global_error_handlers(app):
    """Global exception handler — catches raw errors and returns structured JSON responses"""
    @app.errorhandler(Exception)
    def handle_unhandled_exception(e):
        app.logger.error("Unhandled Exception: %s", str(e), exc_info=True)
        if request.path.startswith("/api/"):
            return api_response(
                success=False,
                error={"code": "INTERNAL_SERVER_ERROR", "message": "An unexpected server error occurred."},
                status=500
            )
        raise e
