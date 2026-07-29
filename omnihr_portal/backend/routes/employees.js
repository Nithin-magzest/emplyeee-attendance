const express = require('express');
const router = express.Router();
const { allAsync, getAsync, runAsync } = require('../database/init');
const { verifyToken, requireAdmin } = require('../middleware/auth');
const { v4: uuidv4 } = require('uuid');

// GET /api/employees — Admin: all, Employee: own only
router.get('/', verifyToken, async (req, res) => {
  try {
    const db = req.app.locals.db;
    const isAdmin = ['super_admin', 'hr_manager'].includes(req.user.role);
    let rows;
    if (isAdmin) {
      rows = await allAsync(db, `
        SELECT e.*, d.name as department_name, le.name as entity_name
        FROM employees e
        LEFT JOIN departments d ON e.department_id = d.id
        LEFT JOIN legal_entities le ON e.legal_entity_id = le.id
        ORDER BY e.first_name`);
    } else {
      rows = await allAsync(db, `
        SELECT e.*, d.name as department_name, le.name as entity_name
        FROM employees e
        LEFT JOIN departments d ON e.department_id = d.id
        LEFT JOIN legal_entities le ON e.legal_entity_id = le.id
        WHERE e.id = ?`, [req.user.empId]);
    }
    res.json(rows);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /api/employees/:id
router.get('/:id', verifyToken, async (req, res) => {
  try {
    const db = req.app.locals.db;
    const isAdmin = ['super_admin', 'hr_manager'].includes(req.user.role);
    if (!isAdmin && req.user.empId !== req.params.id) {
      return res.status(403).json({ error: 'Access denied.' });
    }
    const row = await getAsync(db, `
      SELECT e.*, d.name as department_name, le.name as entity_name
      FROM employees e
      LEFT JOIN departments d ON e.department_id = d.id
      LEFT JOIN legal_entities le ON e.legal_entity_id = le.id
      WHERE e.id = ?`, [req.params.id]);
    if (!row) return res.status(404).json({ error: 'Employee not found.' });
    res.json(row);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// POST /api/employees — Admin only
router.post('/', verifyToken, requireAdmin, async (req, res) => {
  try {
    const db = req.app.locals.db;
    const { firstName, lastName, email, roleTitle, departmentId, legalEntityId, location, salary, currency, joinedDate } = req.body;
    const empId = `EMP-${Date.now()}`;
    const empCode = `OHR-${Math.floor(Math.random() * 9000 + 1000)}`;
    const userId = `USR-${Date.now()}`;
    const bcrypt = require('bcryptjs');
    const tempPassword = 'Welcome@OmniHR2026';
    const hash = bcrypt.hashSync(tempPassword, 12);

    await runAsync(db, 'INSERT INTO users (id, email, password_hash, role) VALUES (?,?,?,?)',
      [userId, email, hash, 'employee']);
    await runAsync(db, `INSERT INTO employees (id, user_id, emp_code, first_name, last_name, email, role_title, department_id, legal_entity_id, location, base_salary, currency, joined_date) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)`,
      [empId, userId, empCode, firstName, lastName, email, roleTitle, departmentId, legalEntityId, location, salary || 50000, currency || 'USD', joinedDate || new Date().toISOString().split('T')[0]]);
    await runAsync(db, 'INSERT INTO leave_balances (id, employee_id) VALUES (?,?)', [uuidv4(), empId]);

    await runAsync(db, 'INSERT INTO audit_logs (id, user_id, action, resource, ip_address) VALUES (?,?,?,?,?)',
      [uuidv4(), req.user.userId, 'CREATE_EMPLOYEE', empId, req.ip]);

    const newEmp = await getAsync(db, 'SELECT * FROM employees WHERE id = ?', [empId]);
    res.status(201).json({ ...newEmp, tempPassword });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// PUT /api/employees/:id — Admin or own profile
router.put('/:id', verifyToken, async (req, res) => {
  try {
    const db = req.app.locals.db;
    const isAdmin = ['super_admin', 'hr_manager'].includes(req.user.role);
    if (!isAdmin && req.user.empId !== req.params.id) {
      return res.status(403).json({ error: 'Access denied.' });
    }
    const { firstName, lastName, phone, location } = req.body;
    await runAsync(db, 'UPDATE employees SET first_name=?, last_name=?, phone=?, location=? WHERE id=?',
      [firstName, lastName, phone, location, req.params.id]);
    const updated = await getAsync(db, 'SELECT * FROM employees WHERE id=?', [req.params.id]);
    res.json(updated);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /api/employees/devices — IT Devices (admin only)
router.get('/all/devices', verifyToken, requireAdmin, async (req, res) => {
  try {
    const db = req.app.locals.db;
    const rows = await allAsync(db, `
      SELECT d.*, e.first_name || ' ' || e.last_name as employee_name, e.avatar_url, e.role_title
      FROM it_devices d
      LEFT JOIN employees e ON d.assigned_employee_id = e.id`);
    res.json(rows);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;
