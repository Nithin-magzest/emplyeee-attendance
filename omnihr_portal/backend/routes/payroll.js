const express = require('express');
const router = express.Router();
const { allAsync, getAsync, runAsync } = require('../database/init');
const { verifyToken, requireAdmin } = require('../middleware/auth');
const { v4: uuidv4 } = require('uuid');

// GET /api/payroll/runs — Admin: all, Employee: own items only
router.get('/runs', verifyToken, requireAdmin, async (req, res) => {
  try {
    const db = req.app.locals.db;
    const runs = await allAsync(db, `
      SELECT pr.*, le.name as entity_name, le.country
      FROM payroll_runs pr
      LEFT JOIN legal_entities le ON pr.legal_entity_id = le.id
      ORDER BY pr.created_at DESC`);
    res.json(runs);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /api/payroll/items — Employee: own items only
router.get('/items', verifyToken, async (req, res) => {
  try {
    const db = req.app.locals.db;
    const isAdmin = ['super_admin', 'hr_manager'].includes(req.user.role);
    let items;
    if (isAdmin) {
      items = await allAsync(db, `
        SELECT pi.*, e.first_name || ' ' || e.last_name as emp_name, e.emp_code, e.avatar_url,
               pr.pay_period, pr.payout_date
        FROM payroll_items pi
        JOIN employees e ON pi.employee_id = e.id
        JOIN payroll_runs pr ON pi.payroll_run_id = pr.id
        ORDER BY pi.created_at DESC`);
    } else {
      items = await allAsync(db, `
        SELECT pi.*, pr.pay_period, pr.payout_date
        FROM payroll_items pi
        JOIN payroll_runs pr ON pi.payroll_run_id = pr.id
        WHERE pi.employee_id = ?
        ORDER BY pi.created_at DESC`, [req.user.empId]);
    }
    res.json(items);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// POST /api/payroll/run — Admin: trigger payroll run
router.post('/run', verifyToken, requireAdmin, async (req, res) => {
  try {
    const db = req.app.locals.db;
    const { payPeriod, legalEntityId } = req.body;
    const employees = await allAsync(db, 'SELECT * FROM employees WHERE status = ? AND legal_entity_id = ?', ['Active', legalEntityId]);
    let totalGross = 0, totalNet = 0, totalTaxes = 0;
    const prId = uuidv4();
    const payout = new Date();
    payout.setDate(payout.getDate() + 3);

    for (const emp of employees) {
      const monthly = emp.base_salary / 12;
      const tax = monthly * 0.27;
      const net = monthly - tax;
      totalGross += monthly;
      totalTaxes += tax;
      totalNet += net;
      await runAsync(db, 'INSERT INTO payroll_items (id, payroll_run_id, employee_id, base_pay, tax_deductions, net_pay, currency, status) VALUES (?,?,?,?,?,?,?,?)',
        [uuidv4(), prId, emp.id, monthly, tax, net, emp.currency, 'Approved']);
    }

    await runAsync(db, 'INSERT INTO payroll_runs (id, pay_period, legal_entity_id, total_gross, total_net, total_taxes, currency, payout_date, status) VALUES (?,?,?,?,?,?,?,?,?)',
      [prId, payPeriod, legalEntityId, totalGross, totalNet, totalTaxes, 'USD', payout.toISOString().split('T')[0], 'Processing']);

    await runAsync(db, 'INSERT INTO audit_logs (id, user_id, action, resource, ip_address) VALUES (?,?,?,?,?)',
      [uuidv4(), req.user.userId, 'PAYROLL_RUN', prId, req.ip]);

    const run = await getAsync(db, 'SELECT * FROM payroll_runs WHERE id = ?', [prId]);
    res.status(201).json(run);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /api/payroll/ewa — EWA requests
router.get('/ewa', verifyToken, async (req, res) => {
  try {
    const db = req.app.locals.db;
    const isAdmin = ['super_admin', 'hr_manager'].includes(req.user.role);
    let rows;
    if (isAdmin) {
      rows = await allAsync(db, `
        SELECT ew.*, e.first_name || ' ' || e.last_name as emp_name, e.avatar_url
        FROM ewa_requests ew
        JOIN employees e ON ew.employee_id = e.id
        ORDER BY ew.transferred_at DESC`);
    } else {
      rows = await allAsync(db, 'SELECT * FROM ewa_requests WHERE employee_id = ? ORDER BY transferred_at DESC', [req.user.empId]);
    }
    res.json(rows);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// POST /api/payroll/ewa — Request EWA
router.post('/ewa', verifyToken, async (req, res) => {
  try {
    const db = req.app.locals.db;
    const empId = req.user.empId;
    if (!empId) return res.status(400).json({ error: 'No employee profile found.' });
    const { requestedAmount } = req.body;
    const emp = await getAsync(db, 'SELECT base_salary FROM employees WHERE id = ?', [empId]);
    const earned = (emp.base_salary / 12) * 0.5;
    if (requestedAmount > earned) return res.status(400).json({ error: `Requested amount exceeds your earned limit of ${earned.toFixed(2)}.` });

    const id = uuidv4();
    await runAsync(db, 'INSERT INTO ewa_requests (id, employee_id, earned_amount, requested_amount, status) VALUES (?,?,?,?,?)',
      [id, empId, earned, requestedAmount, 'Transferred']);
    res.status(201).json({ success: true, id, requestedAmount, earnedAmount: earned, status: 'Transferred' });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /api/payroll/entities — Legal entities
router.get('/entities', verifyToken, requireAdmin, async (req, res) => {
  try {
    const db = req.app.locals.db;
    const rows = await allAsync(db, 'SELECT * FROM legal_entities ORDER BY country');
    res.json(rows);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;
