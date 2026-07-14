"""Face-recognition bootstrap + known-encoding cache.

Extracted from app.py — used by both the employees blueprint (photo
registration/update, which validates a face is detectable in the uploaded
photo) and the attendance blueprint (check-in face-match verification), so
neither can own it exclusively without the other importing across a
blueprint boundary.
"""
import os

try:
    import face_recognition
    _face_recognition_available = True
except Exception as _fr_err:
    face_recognition = None
    _face_recognition_available = False
    print(f"⚠  face_recognition unavailable ({_fr_err}). Face features disabled.")

# Cache known face encodings by (employee_id, file_mtime) to avoid recomputing on every punch
_face_enc_cache: dict = {}


def _get_known_face_encoding(emp_id: str, face_path: str):
    """Return the cached face encoding for an employee, recomputing only when the file changes."""
    try:
        mtime = os.path.getmtime(face_path)
    except OSError:
        return None
    cached = _face_enc_cache.get(emp_id)
    if cached and cached[0] == mtime:
        return cached[1]
    img  = face_recognition.load_image_file(face_path)
    encs = face_recognition.face_encodings(img)
    enc  = encs[0] if encs else None
    _face_enc_cache[emp_id] = (mtime, enc)
    return enc
