const sqlite3 = require('sqlite3').verbose();
const bcrypt = require('bcryptjs');
const path = require('path');
const { v4: uuidv4 } = require('uuid');

const DB_PATH = path.join(__dirname, 'omnihr.db');

function getDb() {
  return new sqlite3.Database(DB_PATH);
}

function runAsync(db, sql, params = []) {
  return new Promise((resolve, reject) => {
    db.run(sql, params, function (err) {
      if (err) reject(err);
      else resolve(this);
    });
  });
}

function getAsync(db, sql, params = []) {
  return new Promise((resolve, reject) => {
    db.get(sql, params, (err, row) => {
      if (err) reject(err);
      else resolve(row);
    });
  });
}

function allAsync(db, sql, params = []) {
  return new Promise((resolve, reject) => {
    db.all(sql, params, (err, rows) => {
      if (err) reject(err);
      else resolve(rows);
    });
  });
}

async function initDatabase() {
  const db = getDb();

  await new Promise((resolve, reject) => {
    db.serialize(async () => {
      try {
        await runAsync(db, 'PRAGMA journal_mode = WAL');
        await runAsync(db, 'PRAGMA foreign_keys = ON');

        const schema = `
          CREATE TABLE IF NOT EXISTS legal_entities (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, country TEXT NOT NULL,
            currency TEXT DEFAULT 'USD', tax_id TEXT,
            created_at TEXT DEFAULT (datetime('now'))
          );
          CREATE TABLE IF NOT EXISTS departments (
            id TEXT PRIMARY KEY, name TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
          );
          CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'employee',
            is_active INTEGER DEFAULT 1, last_login TEXT,
            created_at TEXT DEFAULT (datetime('now'))
          );
          CREATE TABLE IF NOT EXISTS employees (
            id TEXT PRIMARY KEY, user_id TEXT REFERENCES users(id),
            emp_code TEXT UNIQUE NOT NULL, first_name TEXT NOT NULL, last_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL, phone TEXT, role_title TEXT NOT NULL,
            department_id TEXT REFERENCES departments(id),
            legal_entity_id TEXT REFERENCES legal_entities(id),
            manager_id TEXT REFERENCES employees(id),
            location TEXT NOT NULL, employment_type TEXT DEFAULT 'Full-Time',
            status TEXT DEFAULT 'Active', base_salary REAL NOT NULL,
            currency TEXT DEFAULT 'USD', joined_date TEXT NOT NULL, avatar_url TEXT,
            performance_rating REAL DEFAULT 4.5, attrition_risk TEXT DEFAULT 'Low',
            created_at TEXT DEFAULT (datetime('now'))
          );
          CREATE TABLE IF NOT EXISTS it_devices (
            id TEXT PRIMARY KEY, device_name TEXT NOT NULL,
            assigned_employee_id TEXT REFERENCES employees(id),
            serial_number TEXT UNIQUE NOT NULL, device_type TEXT DEFAULT 'Laptop',
            mdm_status TEXT DEFAULT 'Encrypted & Compliant',
            status TEXT DEFAULT 'Active', last_sync_at TEXT DEFAULT (datetime('now')),
            created_at TEXT DEFAULT (datetime('now'))
          );
          CREATE TABLE IF NOT EXISTS payroll_runs (
            id TEXT PRIMARY KEY, pay_period TEXT NOT NULL,
            legal_entity_id TEXT REFERENCES legal_entities(id),
            total_gross REAL NOT NULL, total_net REAL NOT NULL, total_taxes REAL NOT NULL,
            currency TEXT DEFAULT 'USD', payout_date TEXT NOT NULL,
            status TEXT DEFAULT 'Processing', created_at TEXT DEFAULT (datetime('now'))
          );
          CREATE TABLE IF NOT EXISTS payroll_items (
            id TEXT PRIMARY KEY, payroll_run_id TEXT REFERENCES payroll_runs(id),
            employee_id TEXT REFERENCES employees(id),
            base_pay REAL NOT NULL, bonus_allowances REAL DEFAULT 0,
            tax_deductions REAL DEFAULT 0, net_pay REAL NOT NULL,
            currency TEXT DEFAULT 'USD', status TEXT DEFAULT 'Approved',
            created_at TEXT DEFAULT (datetime('now'))
          );
          CREATE TABLE IF NOT EXISTS ewa_requests (
            id TEXT PRIMARY KEY, employee_id TEXT REFERENCES employees(id),
            earned_amount REAL NOT NULL, requested_amount REAL NOT NULL,
            currency TEXT DEFAULT 'USD', status TEXT DEFAULT 'Transferred',
            transfer_fee REAL DEFAULT 0, transferred_at TEXT DEFAULT (datetime('now'))
          );
          CREATE TABLE IF NOT EXISTS attendance_logs (
            id TEXT PRIMARY KEY, employee_id TEXT REFERENCES employees(id),
            check_in_time TEXT NOT NULL, check_out_time TEXT,
            verification_mode TEXT DEFAULT 'Biometric AI Punch',
            gps_latitude REAL, gps_longitude REAL, location_name TEXT,
            status TEXT DEFAULT 'On Time', created_at TEXT DEFAULT (datetime('now'))
          );
          CREATE TABLE IF NOT EXISTS leave_balances (
            id TEXT PRIMARY KEY, employee_id TEXT REFERENCES employees(id) UNIQUE,
            pto_available INTEGER DEFAULT 20, sick_available INTEGER DEFAULT 8,
            casual_available INTEGER DEFAULT 5, updated_at TEXT DEFAULT (datetime('now'))
          );
          CREATE TABLE IF NOT EXISTS pto_requests (
            id TEXT PRIMARY KEY, employee_id TEXT REFERENCES employees(id),
            leave_type TEXT NOT NULL, start_date TEXT NOT NULL, end_date TEXT NOT NULL,
            total_days INTEGER NOT NULL, reason TEXT,
            status TEXT DEFAULT 'Pending Manager Approval',
            approved_by TEXT REFERENCES employees(id),
            created_at TEXT DEFAULT (datetime('now'))
          );
          CREATE TABLE IF NOT EXISTS ats_jobs (
            id TEXT PRIMARY KEY, title TEXT NOT NULL,
            department_id TEXT REFERENCES departments(id),
            location TEXT NOT NULL, salary_range TEXT,
            status TEXT DEFAULT 'Open', created_at TEXT DEFAULT (datetime('now'))
          );
          CREATE TABLE IF NOT EXISTS ats_candidates (
            id TEXT PRIMARY KEY, job_id TEXT REFERENCES ats_jobs(id),
            full_name TEXT NOT NULL, email TEXT NOT NULL, stage TEXT DEFAULT 'Sourcing',
            ai_fit_score INTEGER DEFAULT 85, ai_match_summary TEXT,
            offer_status TEXT DEFAULT 'Pending', applied_at TEXT DEFAULT (datetime('now'))
          );
          CREATE TABLE IF NOT EXISTS performance_ratings (
            id TEXT PRIMARY KEY, employee_id TEXT REFERENCES employees(id),
            performance_level TEXT DEFAULT 'High', potential_level TEXT DEFAULT 'High',
            box_classification TEXT DEFAULT 'Star (Top 10%)',
            evaluation_cycle TEXT DEFAULT 'Q3 2026',
            created_at TEXT DEFAULT (datetime('now'))
          );
          CREATE TABLE IF NOT EXISTS okr_goals (
            id TEXT PRIMARY KEY, title TEXT NOT NULL,
            owner_id TEXT REFERENCES employees(id),
            department_id TEXT REFERENCES departments(id),
            progress_percentage INTEGER DEFAULT 0, target_date TEXT,
            created_at TEXT DEFAULT (datetime('now'))
          );
          CREATE TABLE IF NOT EXISTS feedback_360 (
            id TEXT PRIMARY KEY, target_employee_id TEXT REFERENCES employees(id),
            reviewer_id TEXT REFERENCES employees(id), feedback_text TEXT NOT NULL,
            ai_sentiment_score TEXT DEFAULT '+92% Positive',
            created_at TEXT DEFAULT (datetime('now'))
          );
          CREATE TABLE IF NOT EXISTS ai_workflows (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, trigger_event TEXT NOT NULL,
            actions_json TEXT NOT NULL, status TEXT DEFAULT 'Active',
            executions_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
          );
          CREATE TABLE IF NOT EXISTS audit_logs (
            id TEXT PRIMARY KEY, user_id TEXT REFERENCES users(id),
            action TEXT NOT NULL, resource TEXT, ip_address TEXT,
            created_at TEXT DEFAULT (datetime('now'))
          );
        `;

        for (const stmt of schema.split(';').filter(s => s.trim())) {
          await runAsync(db, stmt);
        }

        const row = await getAsync(db, 'SELECT COUNT(*) as count FROM users');
        if (row.count === 0) {
          console.log('[DB] Seeding initial data...');
          await seedData(db);
          console.log('[DB] Seed complete!');
        } else {
          console.log('[DB] Database already seeded, skipping.');
        }
        resolve();
      } catch (err) {
        reject(err);
      }
    });
  });

  return db;
}

async function seedData(db) {
  const SALT_ROUNDS = 12;

  const entities = [
    ['ENT-001', 'OmniHR Technologies Inc.', 'United States', 'USD', 'EIN-84-2910492'],
    ['ENT-002', 'OmniHR UK Ltd', 'United Kingdom', 'GBP', 'GB-449012381'],
    ['ENT-003', 'OmniHR Tech India Pvt Ltd', 'India', 'INR', 'GSTIN-29AAACR5055K1ZK'],
    ['ENT-004', 'OmniHR France SAS', 'France', 'EUR', 'SIREN-822334510'],
    ['ENT-005', 'OmniHR Germany GmbH', 'Germany', 'EUR', 'DE-812345678'],
  ];
  for (const e of entities) {
    await runAsync(db, 'INSERT INTO legal_entities (id, name, country, currency, tax_id) VALUES (?,?,?,?,?)', e);
  }

  const depts = [
    ['DEPT-001','Human Resources'],['DEPT-002','Engineering'],
    ['DEPT-003','Design'],['DEPT-004','Sales'],['DEPT-005','Finance'],
  ];
  for (const d of depts) await runAsync(db, 'INSERT INTO departments (id, name) VALUES (?,?)', d);

  const usersData = [
    { userId:'USR-001', role:'super_admin', email:'admin@omnihr.io', password:'Admin@123', empId:null },
    { userId:'USR-002', role:'hr_manager', email:'hr@omnihr.io', password:'HRManager@2026',
      empId:'EMP-001', empCode:'OHR-9402', firstName:'Alexander', lastName:'Vance',
      roleTitle:'Chief People Officer', deptId:'DEPT-001', entityId:'ENT-001',
      location:'New York, USA', salary:185000, currency:'USD', joined:'2021-03-15',
      avatar:'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80',
      rating:4.9, risk:'Low', managerId:null },
    { userId:'USR-003', role:'employee', email:'s.martinez@omnihr.io', password:'Employee@123',
      empId:'EMP-002', empCode:'OHR-9403', firstName:'Sophia', lastName:'Martinez',
      roleTitle:'VP of Software Engineering', deptId:'DEPT-002', entityId:'ENT-001',
      location:'San Francisco, USA', salary:210000, currency:'USD', joined:'2020-08-10',
      avatar:'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=150&auto=format&fit=crop&q=80',
      rating:4.8, risk:'Low', managerId:'EMP-001' },
    { userId:'USR-004', role:'employee', email:'m.chen@omnihr.io', password:'Employee@123',
      empId:'EMP-003', empCode:'OHR-9404', firstName:'Marcus', lastName:'Chen',
      roleTitle:'Lead DevOps Engineer', deptId:'DEPT-002', entityId:'ENT-002',
      location:'London, UK', salary:95000, currency:'GBP', joined:'2021-06-01',
      avatar:'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80',
      rating:4.6, risk:'Medium', managerId:'EMP-002' },
    { userId:'USR-005', role:'employee', email:'p.sharma@omnihr.io', password:'Employee@123',
      empId:'EMP-004', empCode:'OHR-9405', firstName:'Priya', lastName:'Sharma',
      roleTitle:'Senior Product Designer', deptId:'DEPT-003', entityId:'ENT-003',
      location:'Bengaluru, India', salary:3200000, currency:'INR', joined:'2022-01-10',
      avatar:'https://images.unsplash.com/photo-1580489944761-15a19d654956?w=150&auto=format&fit=crop&q=80',
      rating:4.9, risk:'Low', managerId:'EMP-001' },
    { userId:'USR-006', role:'employee', email:'d.dubois@omnihr.io', password:'Employee@123',
      empId:'EMP-005', empCode:'OHR-9406', firstName:'David', lastName:'Dubois',
      roleTitle:'Head of EMEA Sales', deptId:'DEPT-004', entityId:'ENT-004',
      location:'Paris, France', salary:130000, currency:'EUR', joined:'2019-11-05',
      avatar:'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150&auto=format&fit=crop&q=80',
      rating:4.2, risk:'High', managerId:'EMP-001' },
    { userId:'USR-007', role:'employee', email:'e.rostova@omnihr.io', password:'Employee@123',
      empId:'EMP-006', empCode:'OHR-9407', firstName:'Elena', lastName:'Rostova',
      roleTitle:'Senior Data Scientist', deptId:'DEPT-002', entityId:'ENT-005',
      location:'Berlin, Germany', salary:92000, currency:'EUR', joined:'2022-03-20',
      avatar:'https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=150&auto=format&fit=crop&q=80',
      rating:4.7, risk:'Low', managerId:'EMP-002' },
  ];

  for (const u of usersData) {
    const hash = bcrypt.hashSync(u.password, SALT_ROUNDS);
    await runAsync(db, 'INSERT INTO users (id, email, password_hash, role) VALUES (?,?,?,?)',
      [u.userId, u.email, hash, u.role]);
    if (u.empId) {
      await runAsync(db, `INSERT INTO employees (id, user_id, emp_code, first_name, last_name, email, phone, role_title, department_id, legal_entity_id, manager_id, location, employment_type, status, base_salary, currency, joined_date, avatar_url, performance_rating, attrition_risk) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`,
        [u.empId, u.userId, u.empCode, u.firstName, u.lastName, u.email, '+1 555 000 0000', u.roleTitle, u.deptId, u.entityId, u.managerId, u.location, 'Full-Time', 'Active', u.salary, u.currency, u.joined, u.avatar, u.rating, u.risk]);
    }
  }

  // IT Devices
  const devices = [
    ['DEV-101','MacBook Pro M3 Max 16"','EMP-001','C02G9912LMSP','Laptop','Encrypted & Compliant','Active'],
    ['DEV-102','MacBook Pro M3 Pro 14"','EMP-002','C02FX910PQL1','Laptop','Encrypted & Compliant','Active'],
    ['DEV-103','Dell XPS 15 9530','EMP-003','DLX-88231-UK','Laptop','Update Pending','Active'],
    ['DEV-104','MacBook Air M2 15"','EMP-004','C02H1109LA11','Laptop','Encrypted & Compliant','Active'],
    ['DEV-105','ThinkPad X1 Carbon Gen 11','EMP-005','TP-99201-FR','Laptop','Compliance Flagged','Action Required'],
  ];
  for (const d of devices) {
    await runAsync(db, 'INSERT INTO it_devices (id, device_name, assigned_employee_id, serial_number, device_type, mdm_status, status) VALUES (?,?,?,?,?,?,?)', d);
  }

  // Leave balances
  const empIds = ['EMP-001','EMP-002','EMP-003','EMP-004','EMP-005','EMP-006'];
  for (let i = 0; i < empIds.length; i++) {
    await runAsync(db, 'INSERT INTO leave_balances (id, employee_id, pto_available, sick_available, casual_available) VALUES (?,?,?,?,?)',
      [uuidv4(), empIds[i], 18 - i, 7, 4]);
  }

  // Attendance
  const today = new Date().toISOString().split('T')[0];
  const attLogs = [
    [uuidv4(),'EMP-001',`${today}T08:54:00`,'Biometric AI Punch','New York HQ','On Time'],
    [uuidv4(),'EMP-002',`${today}T09:02:00`,'WebCam Face ID','SF Office','On Time'],
    [uuidv4(),'EMP-003',`${today}T08:45:00`,'Mobile GPS Punch','Remote - London','On Time'],
    [uuidv4(),'EMP-004',`${today}T09:30:00`,'Biometric AI Punch','BLR Tech Park','Late (15m)'],
  ];
  for (const a of attLogs) {
    await runAsync(db, 'INSERT INTO attendance_logs (id, employee_id, check_in_time, verification_mode, location_name, status) VALUES (?,?,?,?,?,?)', a);
  }

  // PTO requests
  await runAsync(db, 'INSERT INTO pto_requests (id, employee_id, leave_type, start_date, end_date, total_days, reason, status) VALUES (?,?,?,?,?,?,?,?)',
    [uuidv4(),'EMP-006','Annual PTO','2026-08-04','2026-08-10',5,'Family Vacation','Pending Manager Approval']);
  await runAsync(db, 'INSERT INTO pto_requests (id, employee_id, leave_type, start_date, end_date, total_days, reason, status) VALUES (?,?,?,?,?,?,?,?)',
    [uuidv4(),'EMP-005','Sick Leave','2026-07-28','2026-07-29',2,'Medical Visit','Approved']);

  // ATS
  await runAsync(db,'INSERT INTO ats_jobs (id,title,department_id,location,salary_range,status) VALUES (?,?,?,?,?,?)',
    ['JOB-001','Principal AI Engineer','DEPT-002','Remote / San Francisco','$180,000 - $230,000','Open']);
  await runAsync(db,'INSERT INTO ats_jobs (id,title,department_id,location,salary_range,status) VALUES (?,?,?,?,?,?)',
    ['JOB-002','Senior Product Designer','DEPT-003','New York / Remote','$130,000 - $160,000','Open']);

  const candidates = [
    [uuidv4(),'JOB-001','Dr. Jonathan Hayes','j.hayes@candidate.io','Interview',96,'Exceptional fit in PyTorch & LLM deployment. Previous lead at DeepMind.','Pending'],
    [uuidv4(),'JOB-002','Claire Lin','c.lin@candidate.io','Offer Sent',92,'Top tier portfolio in enterprise SaaS & Figma Design Tokens.','Offer Sent'],
    [uuidv4(),'JOB-001','Tariq Al-Mansoor','t.almansoor@candidate.io','Screening',88,'Strong Kubernetes & multi-cloud security track record.','Pending'],
    [uuidv4(),'JOB-001','Sarah Jenkins','s.jenkins@candidate.io','Sourcing',84,'Experience scaling EMEA workforce from 50 to 500.','Pending'],
  ];
  for (const c of candidates) {
    await runAsync(db,'INSERT INTO ats_candidates (id,job_id,full_name,email,stage,ai_fit_score,ai_match_summary,offer_status) VALUES (?,?,?,?,?,?,?,?)', c);
  }

  // Performance
  const perfData = [
    ['EMP-001','High','High','Star (Top 10%)'],['EMP-002','High','High','Star (Top 10%)'],
    ['EMP-003','High','Medium','High Performer'],['EMP-004','High','High','Star (Top 10%)'],
    ['EMP-005','Medium','High','High Potential'],['EMP-006','High','High','Star (Top 10%)'],
  ];
  for (const p of perfData) {
    await runAsync(db,'INSERT INTO performance_ratings (id,employee_id,performance_level,potential_level,box_classification) VALUES (?,?,?,?,?)',
      [uuidv4(),...p]);
  }

  // OKR
  await runAsync(db,'INSERT INTO okr_goals (id,title,owner_id,department_id,progress_percentage,target_date) VALUES (?,?,?,?,?,?)',
    [uuidv4(),'Scale European Customer Base by 30%','EMP-005','DEPT-004',78,'2026-12-31']);
  await runAsync(db,'INSERT INTO okr_goals (id,title,owner_id,department_id,progress_percentage,target_date) VALUES (?,?,?,?,?,?)',
    [uuidv4(),'Reduce Platform API Latency to < 50ms','EMP-002','DEPT-002',92,'2026-09-30']);
  await runAsync(db,'INSERT INTO okr_goals (id,title,owner_id,department_id,progress_percentage,target_date) VALUES (?,?,?,?,?,?)',
    [uuidv4(),'Deploy AI Resume Sourcing Engine','EMP-001','DEPT-001',85,'2026-10-15']);

  // 360 feedback
  await runAsync(db,'INSERT INTO feedback_360 (id,target_employee_id,reviewer_id,feedback_text,ai_sentiment_score) VALUES (?,?,?,?,?)',
    [uuidv4(),'EMP-004','EMP-002','Priya delivered exceptional design tokens for our HR portal. Highly collaborative and proactive.','+94% Positive']);
  await runAsync(db,'INSERT INTO feedback_360 (id,target_employee_id,reviewer_id,feedback_text,ai_sentiment_score) VALUES (?,?,?,?,?)',
    [uuidv4(),'EMP-003','EMP-006','Marcus streamlined our Kubernetes cluster deployment across EMEA without downtime.','+88% Positive']);

  // AI Workflows
  await runAsync(db,'INSERT INTO ai_workflows (id,name,trigger_event,actions_json,executions_count) VALUES (?,?,?,?,?)',
    [uuidv4(),'Automated Global Onboarding','New Hire Status -> Signed Offer',JSON.stringify(['Create Workday ID','Order Apple Laptop via IT Hub','Send Welcome Email']),12]);
  await runAsync(db,'INSERT INTO ai_workflows (id,name,trigger_event,actions_json,executions_count) VALUES (?,?,?,?,?)',
    [uuidv4(),'Predictive Attrition Risk Alert',"AI Sentiment Analysis drops < 65%",JSON.stringify(['Flag in 9-Box Matrix','Notify HR Business Partner','Schedule 1-on-1 Retention Check']),3]);
  await runAsync(db,'INSERT INTO ai_workflows (id,name,trigger_event,actions_json,executions_count) VALUES (?,?,?,?,?)',
    [uuidv4(),'Earned Wage Instant Disbursement','EWA Request < 50% Earned Salary',JSON.stringify(['Check Payroll Ledger','Execute Bank API Transfer','Update Next Paystub Deduction']),28]);

  // Payroll
  const prId = uuidv4();
  await runAsync(db,'INSERT INTO payroll_runs (id,pay_period,legal_entity_id,total_gross,total_net,total_taxes,currency,payout_date,status) VALUES (?,?,?,?,?,?,?,?,?)',
    [prId,'July 2026','ENT-001',485000,362400,122600,'USD','2026-07-31','Processing']);
  const payItems = [
    [uuidv4(),prId,'EMP-001',15416,2000,4200,13216,'USD','Approved'],
    [uuidv4(),prId,'EMP-002',17500,3500,5100,15900,'USD','Approved'],
    [uuidv4(),prId,'EMP-003',7916,800,2100,6616,'GBP','Approved'],
    [uuidv4(),prId,'EMP-004',266666,25000,58000,233666,'INR','Pending Approval'],
  ];
  for (const pi of payItems) {
    await runAsync(db,'INSERT INTO payroll_items (id,payroll_run_id,employee_id,base_pay,bonus_allowances,tax_deductions,net_pay,currency,status) VALUES (?,?,?,?,?,?,?,?,?)', pi);
  }
}

module.exports = { initDatabase, getDb, runAsync, getAsync, allAsync };
