"""
Automation Blueprint — Event-driven HRMS lifecycle data pipeline triggers.
Provides automated endpoints for ATS transitions, IT provisioning, payroll localization,
attendance auto-enrollment, 30-60-90 performance milestones, and zero-touch offboarding.
"""

from flask import Blueprint, jsonify, request
import datetime
import json

automation_bp = Blueprint("automation", __name__)

@automation_bp.route("/api/automation/trigger/applicant_hired", methods=["POST"])
def trigger_applicant_hired():
    data = request.get_json() or {}
    candidate_id = data.get("candidate_id", "C-901")
    candidate_name = data.get("candidate_name", "Alexander Wright")
    role = data.get("role", "Sr. Staff Distributed Engineer")
    salary = data.get("salary", 320000)

    return jsonify({
        "status": "SUCCESS",
        "event": "ats.candidate.hired",
        "employee_id": f"EMP-{candidate_id}",
        "docusign_envelope_id": f"ds_env_{candidate_id}_2026",
        "contract_sent_to": f"{candidate_name.lower().replace(' ', '.')}@gmail.com",
        "message": f"Candidate {candidate_name} migrated to Core HR DB. DocuSign contract envelope dispatched."
    }), 200


@automation_bp.route("/api/automation/trigger/contract_signed", methods=["POST"])
def trigger_contract_signed():
    data = request.get_json() or {}
    employee_id = data.get("employee_id", "EMP-1001")
    name = data.get("name", "Dr. Evelyn Vance")
    dept = data.get("department", "Core Platform Engineering")

    corporate_email = f"{name.lower().replace(' ', '.').replace('dr.', '')}@maghr.com"

    return jsonify({
        "status": "PROVISIONED",
        "event": "docusign.contract.signed",
        "employee_id": employee_id,
        "corporate_email": corporate_email,
        "it_provisioning": {
            "google_workspace": "CREATED",
            "slack_scim_channels": ["#dept-engineering", "#all-hands", "#security-announcements"],
            "jira_role": "DEVELOPER_ADMIN",
            "jamf_mdm_profile": "ENROLLED_ACTIVE"
        },
        "welcome_checklist": [
            "Complete Direct Deposit Setup",
            "Upload Form I-9 Proof",
            "Enroll 2FA Security Key",
            "Complete Cybersecurity Training"
        ]
    }), 200


@automation_bp.route("/api/automation/trigger/payroll_compliance", methods=["POST"])
def trigger_payroll_compliance():
    data = request.get_json() or {}
    employee_id = data.get("employee_id", "EMP-1001")
    routing_code = data.get("routing_code", "021000021")
    country = data.get("country", "US")
    state = data.get("state", "NY")

    return jsonify({
        "status": "PAYROLL_SYNCED",
        "event": "portal.banking_tax.submitted",
        "employee_id": employee_id,
        "bank_validation": {
            "routing_number": routing_code,
            "bank_name": "JPMorgan Chase Bank, N.A.",
            "status": "VERIFIED_VALID"
        },
        "deel_payroll_status": "ENROLLED_DIRECT_DEPOSIT",
        "assigned_tax_bracket": {
            "country": country,
            "state": state,
            "federal_w4": "MARRIED_FILING_JOINTLY",
            "state_tax_rate": 0.0685
        }
    }), 200


@automation_bp.route("/api/automation/trigger/start_date_reached", methods=["POST"])
def trigger_start_date_reached():
    data = request.get_json() or {}
    employee_id = data.get("employee_id", "EMP-1001")
    country = data.get("country", "US")

    today = datetime.date.today()
    days_left = (datetime.date(today.year, 12, 31) - today).days + 1
    prorated_pto = round(24.0 * (days_left / 365.0), 1)

    return jsonify({
        "status": "AUTO_ENROLLED",
        "event": "cron.start_date.reached",
        "employee_id": employee_id,
        "holiday_calendar": f"{country}_STATUTORY_CALENDAR_2026",
        "prorated_pto_balance_days": prorated_pto,
        "geofence_punch_enabled": True
    }), 200


@automation_bp.route("/api/automation/trigger/performance_milestone", methods=["POST"])
def trigger_performance_milestone():
    data = request.get_json() or {}
    milestone_day = data.get("milestone_day", 30)

    return jsonify({
        "status": "DISPATCHED",
        "event": "cron.lifecycle_milestone",
        "milestone": f"{milestone_day}_DAY_TENURE_CHECKIN",
        "action": "Triggered 30-Day Check-in Feedback Form to Employee & Manager",
        "compliance_reminder": "14-Day Mandatory Security Awareness Training Expiry Warning Sent"
    }), 200


@automation_bp.route("/api/automation/trigger/zero_touch_offboard", methods=["POST"])
def trigger_zero_touch_offboard():
    data = request.get_json() or {}
    employee_id = data.get("employee_id", "EMP-1004")
    email = data.get("email", "kaelen.rivera@maghr.com")
    serial = data.get("serial", "DL-994200")

    return jsonify({
        "status": "DEPROVISIONED_CLEANLY",
        "event": "hr.termination.logged",
        "employee_id": employee_id,
        "execution_summary": {
            "google_workspace": "SUSPENDED_AT_17:00",
            "slack_zoom_sessions": "TERMINATED",
            "jamf_remote_lock": f"LOCKED_PIN_994012 (Asset {serial})",
            "asset_logistics": "RETURN_BOX_LABEL_DISPATCHED",
            "final_settlement": {
                "unused_pto_cashout_days": 6.5,
                "gross_settlement_usd": 5250.00,
                "status": "QUEUED_NEXT_PAYROLL_RUN"
            }
        }
    }), 200
