-- ====================================================================
-- OmniHR Premier Enterprise HRMS Database Schema
-- Compatible with PostgreSQL 14+ / MySQL 8.0+ / SQLite 3
-- Covers Core HR, IT Hardware, Global Payroll, EWA, Attendance,
-- ATS Recruitment, 9-Box Performance, OKRs, and AI Workflows.
-- ====================================================================

-- 1. Legal Entities & Offices
CREATE TABLE legal_entities (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    country VARCHAR(100) NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    tax_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Departments
CREATE TABLE departments (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    head_emp_id VARCHAR(36),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Core Employees & Profiles
CREATE TABLE employees (
    id VARCHAR(36) PRIMARY KEY,
    emp_code VARCHAR(50) UNIQUE NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(50),
    role_title VARCHAR(150) NOT NULL,
    department_id VARCHAR(36) REFERENCES departments(id),
    legal_entity_id VARCHAR(36) REFERENCES legal_entities(id),
    manager_id VARCHAR(36) REFERENCES employees(id),
    location VARCHAR(150) NOT NULL,
    employment_type VARCHAR(50) DEFAULT 'Full-Time',
    status VARCHAR(50) DEFAULT 'Active',
    base_salary DECIMAL(12, 2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    joined_date DATE NOT NULL,
    avatar_url TEXT,
    performance_rating DECIMAL(3, 2) DEFAULT 4.50,
    attrition_risk VARCHAR(20) DEFAULT 'Low',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. IT Hardware & Device Assets (Rippling Style)
CREATE TABLE it_devices (
    id VARCHAR(36) PRIMARY KEY,
    device_name VARCHAR(255) NOT NULL,
    assigned_employee_id VARCHAR(36) REFERENCES employees(id),
    serial_number VARCHAR(100) UNIQUE NOT NULL,
    device_type VARCHAR(50) DEFAULT 'Laptop',
    mdm_status VARCHAR(100) DEFAULT 'Encrypted & Compliant',
    status VARCHAR(50) DEFAULT 'Active',
    last_sync_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Global Payroll Runs & Ledgers (Gusto / Deel Style)
CREATE TABLE payroll_runs (
    id VARCHAR(36) PRIMARY KEY,
    pay_period VARCHAR(50) NOT NULL,
    legal_entity_id VARCHAR(36) REFERENCES legal_entities(id),
    total_gross DECIMAL(14, 2) NOT NULL,
    total_net DECIMAL(14, 2) NOT NULL,
    total_taxes DECIMAL(14, 2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    payout_date DATE NOT NULL,
    status VARCHAR(50) DEFAULT 'Processing',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE payroll_items (
    id VARCHAR(36) PRIMARY KEY,
    payroll_run_id VARCHAR(36) REFERENCES payroll_runs(id),
    employee_id VARCHAR(36) REFERENCES employees(id),
    base_pay DECIMAL(12, 2) NOT NULL,
    bonus_allowances DECIMAL(12, 2) DEFAULT 0.00,
    tax_deductions DECIMAL(12, 2) DEFAULT 0.00,
    net_pay DECIMAL(12, 2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    status VARCHAR(50) DEFAULT 'Approved',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Earned Wage Access (EWA On-Demand Pay)
CREATE TABLE ewa_requests (
    id VARCHAR(36) PRIMARY KEY,
    employee_id VARCHAR(36) REFERENCES employees(id),
    earned_amount DECIMAL(12, 2) NOT NULL,
    requested_amount DECIMAL(12, 2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    status VARCHAR(50) DEFAULT 'Transferred',
    transfer_fee DECIMAL(6, 2) DEFAULT 0.00,
    transferred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. Biometric & Geofenced Attendance
CREATE TABLE attendance_logs (
    id VARCHAR(36) PRIMARY KEY,
    employee_id VARCHAR(36) REFERENCES employees(id),
    check_in_time TIMESTAMP NOT NULL,
    check_out_time TIMESTAMP,
    verification_mode VARCHAR(100) DEFAULT 'Biometric AI Punch',
    gps_latitude DECIMAL(10, 8),
    gps_longitude DECIMAL(11, 8),
    location_name VARCHAR(255),
    status VARCHAR(50) DEFAULT 'On Time',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. PTO & Absence Management
CREATE TABLE leave_balances (
    id VARCHAR(36) PRIMARY KEY,
    employee_id VARCHAR(36) REFERENCES employees(id),
    pto_available INT DEFAULT 20,
    sick_available INT DEFAULT 8,
    casual_available INT DEFAULT 5,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE pto_requests (
    id VARCHAR(36) PRIMARY KEY,
    employee_id VARCHAR(36) REFERENCES employees(id),
    leave_type VARCHAR(50) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    total_days INT NOT NULL,
    reason TEXT,
    status VARCHAR(50) DEFAULT 'Pending Manager Approval',
    approved_by VARCHAR(36) REFERENCES employees(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 9. ATS Recruitment Pipeline (BambooHR Style)
CREATE TABLE ats_jobs (
    id VARCHAR(36) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    department_id VARCHAR(36) REFERENCES departments(id),
    location VARCHAR(150) NOT NULL,
    salary_range VARCHAR(100),
    status VARCHAR(50) DEFAULT 'Open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ats_candidates (
    id VARCHAR(36) PRIMARY KEY,
    job_id VARCHAR(36) REFERENCES ats_jobs(id),
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    stage VARCHAR(50) DEFAULT 'Sourcing',
    ai_fit_score INT DEFAULT 85,
    ai_match_summary TEXT,
    offer_status VARCHAR(50) DEFAULT 'Pending',
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 10. Performance 9-Box, OKRs & 360 Feedback (Workday Style)
CREATE TABLE performance_ratings (
    id VARCHAR(36) PRIMARY KEY,
    employee_id VARCHAR(36) REFERENCES employees(id),
    performance_level VARCHAR(20) DEFAULT 'High',
    potential_level VARCHAR(20) DEFAULT 'High',
    box_classification VARCHAR(50) DEFAULT 'Star (Top 10%)',
    evaluation_cycle VARCHAR(50) DEFAULT 'Q3 2026',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE okr_goals (
    id VARCHAR(36) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    owner_id VARCHAR(36) REFERENCES employees(id),
    department_id VARCHAR(36) REFERENCES departments(id),
    progress_percentage INT DEFAULT 0,
    target_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE feedback_360 (
    id VARCHAR(36) PRIMARY KEY,
    target_employee_id VARCHAR(36) REFERENCES employees(id),
    reviewer_id VARCHAR(36) REFERENCES employees(id),
    feedback_text TEXT NOT NULL,
    ai_sentiment_score VARCHAR(50) DEFAULT '+92% Positive',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 11. AI Autonomous Workflows (Rippling / Personio Style)
CREATE TABLE ai_workflows (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    trigger_event VARCHAR(255) NOT NULL,
    actions_json JSON NOT NULL,
    status VARCHAR(50) DEFAULT 'Active',
    executions_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
