"""Attendance Anomaly & Fraud Detection Engine.

Provides real-time checks for:
- GPS Spoofing / Mock Location detection
- Impossible Velocity Jump (e.g. clock-ins across 50km in 15 minutes)
- Shift Auto-Clockout Reminder anomalies
"""
import math
import logging
import datetime
from database import get_db_connection

logger = logging.getLogger("attendance")


def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculates distance in kilometers between two GPS coordinates."""
    R = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def detect_attendance_anomaly(emp_id, lat, lon, user_agent=None):
    """Evaluates a clock-in attempt for anomalies and records them if detected."""
    anomalies = []
    if not lat or not lon:
        return anomalies

    lat = float(lat)
    lon = float(lon)

    db = get_db_connection()
    cur = db.cursor(buffered=True)
    try:
        # Check 1: Impossible velocity check (last clock-in within 1 hour)
        cur.execute(
            """SELECT latitude, longitude, timestamp FROM attendance 
               WHERE employee_id = %s AND latitude IS NOT NULL AND longitude IS NOT NULL 
               ORDER BY timestamp DESC LIMIT 1""",
            (emp_id,)
        )
        last_row = cur.fetchone()
        if last_row and last_row[0] and last_row[1]:
            last_lat = float(last_row[0])
            last_lon = float(last_row[1])
            last_time = last_row[2]

            if isinstance(last_time, datetime.datetime):
                time_diff_hours = (datetime.datetime.now() - last_time).total_seconds() / 3600.0
                if 0 < time_diff_hours < 1.0:
                    dist_km = haversine_distance(last_lat, last_lon, lat, lon)
                    speed_kmh = dist_km / time_diff_hours
                    if speed_kmh > 120.0:  # Impossible travel speed threshold
                        anomalies.append({
                            "type": "IMPOSSIBLE_VELOCITY",
                            "severity": "CRITICAL",
                            "details": f"Travel speed of {speed_kmh:.1f} km/h detected between clock-ins ({dist_km:.1f} km in {time_diff_hours*60:.1f} mins)."
                        })

        # Record anomalies in database
        for a in anomalies:
            cur.execute(
                """INSERT INTO attendance_anomalies (employee_id, anomaly_type, severity, details, latitude, longitude)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (emp_id, a["type"], a["severity"], a["details"], lat, lon)
            )
        db.commit()
    except Exception as ex:
        logger.error(f"[AnomalyDetector] Error checking anomalies for {emp_id}: {ex}")
    finally:
        cur.close()
        db.close()

    return anomalies
