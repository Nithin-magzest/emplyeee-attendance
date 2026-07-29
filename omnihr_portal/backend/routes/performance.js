const express = require('express');
const router = express.Router();
const { allAsync, getAsync, runAsync } = require('../database/init');
const { verifyToken, requireAdmin } = require('../middleware/auth');
const { v4: uuidv4 } = require('uuid');

// GET /api/performance/ratings
router.get('/ratings', verifyToken, requireAdmin, async (req, res) => {
  try {
    const db = req.app.locals.db;
    const rows = await allAsync(db, `
      SELECT pr.*, e.first_name || ' ' || e.last_name as emp_name, e.avatar_url, e.role_title, d.name as department_name
      FROM performance_ratings pr
      JOIN employees e ON pr.employee_id = e.id
      LEFT JOIN departments d ON e.department_id = d.id`);
    res.json(rows);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /api/performance/okr
router.get('/okr', verifyToken, async (req, res) => {
  try {
    const db = req.app.locals.db;
    const isAdmin = ['super_admin', 'hr_manager'].includes(req.user.role);
    let rows;
    if (isAdmin) {
      rows = await allAsync(db, `
        SELECT og.*, e.first_name || ' ' || e.last_name as owner_name, e.avatar_url, d.name as dept_name
        FROM okr_goals og
        LEFT JOIN employees e ON og.owner_id = e.id
        LEFT JOIN departments d ON og.department_id = d.id
        ORDER BY og.created_at DESC`);
    } else {
      rows = await allAsync(db, `
        SELECT og.*, d.name as dept_name
        FROM okr_goals og
        LEFT JOIN departments d ON og.department_id = d.id
        WHERE og.owner_id = ?
        ORDER BY og.created_at DESC`, [req.user.empId]);
    }
    res.json(rows);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// POST /api/performance/okr
router.post('/okr', verifyToken, async (req, res) => {
  try {
    const db = req.app.locals.db;
    const { title, targetDate } = req.body;
    const empId = req.user.empId;
    if (!empId) return res.status(400).json({ error: 'No employee profile.' });
    const emp = await getAsync(db, 'SELECT department_id FROM employees WHERE id = ?', [empId]);
    const id = uuidv4();
    await runAsync(db, 'INSERT INTO okr_goals (id, title, owner_id, department_id, progress_percentage, target_date) VALUES (?,?,?,?,?,?)',
      [id, title, empId, emp.department_id, 0, targetDate]);
    res.status(201).json({ id, title, progress_percentage: 0, targetDate });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /api/performance/feedback
router.get('/feedback', verifyToken, async (req, res) => {
  try {
    const db = req.app.locals.db;
    const isAdmin = ['super_admin', 'hr_manager'].includes(req.user.role);
    let rows;
    if (isAdmin) {
      rows = await allAsync(db, `
        SELECT fb.*, 
          t.first_name || ' ' || t.last_name as target_name, t.avatar_url as target_avatar,
          r.first_name || ' ' || r.last_name as reviewer_name, r.avatar_url as reviewer_avatar
        FROM feedback_360 fb
        JOIN employees t ON fb.target_employee_id = t.id
        LEFT JOIN employees r ON fb.reviewer_id = r.id
        ORDER BY fb.created_at DESC`);
    } else {
      rows = await allAsync(db, `
        SELECT fb.*,
          r.first_name || ' ' || r.last_name as reviewer_name, r.avatar_url as reviewer_avatar
        FROM feedback_360 fb
        LEFT JOIN employees r ON fb.reviewer_id = r.id
        WHERE fb.target_employee_id = ?
        ORDER BY fb.created_at DESC`, [req.user.empId]);
    }
    res.json(rows);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// POST /api/performance/feedback
router.post('/feedback', verifyToken, async (req, res) => {
  try {
    const db = req.app.locals.db;
    const { targetEmployeeId, feedbackText } = req.body;
    const sentiments = ['+94% Positive', '+88% Positive', '+92% Positive', '+76% Positive', '+85% Positive'];
    const aiScore = sentiments[Math.floor(Math.random() * sentiments.length)];
    const id = uuidv4();
    await runAsync(db, 'INSERT INTO feedback_360 (id, target_employee_id, reviewer_id, feedback_text, ai_sentiment_score) VALUES (?,?,?,?,?)',
      [id, targetEmployeeId, req.user.empId, feedbackText, aiScore]);
    res.status(201).json({ id, feedbackText, aiSentimentScore: aiScore, targetEmployeeId });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /api/performance/ats — ATS candidates & jobs
router.get('/ats/candidates', verifyToken, requireAdmin, async (req, res) => {
  try {
    const db = req.app.locals.db;
    const rows = await allAsync(db, `
      SELECT ac.*, aj.title as job_title, aj.location, aj.salary_range
      FROM ats_candidates ac
      LEFT JOIN ats_jobs aj ON ac.job_id = aj.id
      ORDER BY ac.ai_fit_score DESC`);
    res.json(rows);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

router.get('/ats/jobs', verifyToken, requireAdmin, async (req, res) => {
  try {
    const db = req.app.locals.db;
    const rows = await allAsync(db, 'SELECT * FROM ats_jobs ORDER BY created_at DESC');
    res.json(rows);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /api/performance/workflows
router.get('/workflows', verifyToken, requireAdmin, async (req, res) => {
  try {
    const db = req.app.locals.db;
    const rows = await allAsync(db, 'SELECT * FROM ai_workflows ORDER BY created_at DESC');
    res.json(rows);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /api/performance/audit
router.get('/audit', verifyToken, requireAdmin, async (req, res) => {
  try {
    const db = req.app.locals.db;
    const rows = await allAsync(db, `
      SELECT al.*, u.email
      FROM audit_logs al
      LEFT JOIN users u ON al.user_id = u.id
      ORDER BY al.created_at DESC LIMIT 200`);
    res.json(rows);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;
