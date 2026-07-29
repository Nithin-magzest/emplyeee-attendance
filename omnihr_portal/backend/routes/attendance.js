const express = require('express');
const router = express.Router();
const { allAsync, getAsync, runAsync } = require('../database/init');
const { verifyToken, requireAdmin } = require('../middleware/auth');
const { v4: uuidv4 } = require('uuid');

// GET /api/attendance — Admin: all, Employee: own only
router.get('/', verifyToken, async (req, res) => {
  try {
    const db = req.app.locals.db;
    const isAdmin = ['super_admin', 'hr_manager'].includes(req.user.role);
    let rows;
    if (isAdmin) {
      rows = await allAsync(db, `
        SELECT al.*, e.first_name || ' ' || e.last_name as emp_name, e.avatar_url, e.role_title, e.emp_code
        FROM attendance_logs al
        JOIN employees e ON al.employee_id = e.id
        ORDER BY al.check_in_time DESC LIMIT 100`);
    } else {
      rows = await allAsync(db, `
        SELECT * FROM attendance_logs WHERE employee_id = ? ORDER BY check_in_time DESC LIMIT 30`,
        [req.user.empId]);
    }
    res.json(rows);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// POST /api/attendance/checkin
router.post('/checkin', verifyToken, async (req, res) => {
  try {
    const db = req.app.locals.db;
    const empId = req.user.empId;
    if (!empId) return res.status(400).json({ error: 'No employee profile.' });
    const { verificationMode, locationName } = req.body;
    const now = new Date();
    const hour = now.getHours();
    const status = hour < 9 ? 'On Time' : hour < 10 ? 'Late (< 1hr)' : 'Late';
    const id = uuidv4();
    await runAsync(db, 'INSERT INTO attendance_logs (id, employee_id, check_in_time, verification_mode, location_name, status) VALUES (?,?,?,?,?,?)',
      [id, empId, now.toISOString(), verificationMode || 'Biometric AI Punch', locationName || 'Office HQ', status]);
    res.status(201).json({ id, check_in_time: now.toISOString(), status });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// PUT /api/attendance/:id/checkout
router.put('/:id/checkout', verifyToken, async (req, res) => {
  try {
    const db = req.app.locals.db;
    const now = new Date().toISOString();
    await runAsync(db, 'UPDATE attendance_logs SET check_out_time = ? WHERE id = ?', [now, req.params.id]);
    res.json({ check_out_time: now });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /api/attendance/leave-balances
router.get('/leave-balances', verifyToken, async (req, res) => {
  try {
    const db = req.app.locals.db;
    const isAdmin = ['super_admin', 'hr_manager'].includes(req.user.role);
    let rows;
    if (isAdmin) {
      rows = await allAsync(db, `
        SELECT lb.*, e.first_name || ' ' || e.last_name as emp_name, e.avatar_url
        FROM leave_balances lb JOIN employees e ON lb.employee_id = e.id`);
    } else {
      rows = await allAsync(db, 'SELECT * FROM leave_balances WHERE employee_id = ?', [req.user.empId]);
    }
    res.json(rows);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /api/attendance/pto-requests
router.get('/pto-requests', verifyToken, async (req, res) => {
  try {
    const db = req.app.locals.db;
    const isAdmin = ['super_admin', 'hr_manager'].includes(req.user.role);
    let rows;
    if (isAdmin) {
      rows = await allAsync(db, `
        SELECT pr.*, e.first_name || ' ' || e.last_name as emp_name, e.avatar_url, e.department_id
        FROM pto_requests pr JOIN employees e ON pr.employee_id = e.id
        ORDER BY pr.created_at DESC`);
    } else {
      rows = await allAsync(db, 'SELECT * FROM pto_requests WHERE employee_id = ? ORDER BY created_at DESC', [req.user.empId]);
    }
    res.json(rows);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// POST /api/attendance/pto-requests
router.post('/pto-requests', verifyToken, async (req, res) => {
  try {
    const db = req.app.locals.db;
    const { leaveType, startDate, endDate, reason } = req.body;
    const empId = req.user.empId;
    if (!empId) return res.status(400).json({ error: 'No employee profile.' });
    const start = new Date(startDate);
    const end = new Date(endDate);
    const days = Math.ceil((end - start) / (1000 * 60 * 60 * 24)) + 1;
    const id = uuidv4();
    await runAsync(db, 'INSERT INTO pto_requests (id, employee_id, leave_type, start_date, end_date, total_days, reason, status) VALUES (?,?,?,?,?,?,?,?)',
      [id, empId, leaveType, startDate, endDate, days, reason, 'Pending Manager Approval']);
    res.status(201).json({ id, leaveType, startDate, endDate, totalDays: days, status: 'Pending Manager Approval' });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// PUT /api/attendance/pto-requests/:id/approve — Admin only
router.put('/pto-requests/:id/approve', verifyToken, requireAdmin, async (req, res) => {
  try {
    const db = req.app.locals.db;
    const { action } = req.body; // 'approve' or 'decline'
    const status = action === 'approve' ? 'Approved' : 'Declined';
    await runAsync(db, 'UPDATE pto_requests SET status = ?, approved_by = ? WHERE id = ?',
      [status, req.user.empId, req.params.id]);
    res.json({ id: req.params.id, status });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;
