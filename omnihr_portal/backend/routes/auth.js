const express = require('express');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const router = express.Router();
const { getAsync, runAsync } = require('../database/init');
const { JWT_SECRET, verifyToken } = require('../middleware/auth');

// POST /api/auth/login
router.post('/login', async (req, res) => {
  const { email, password } = req.body;
  if (!email || !password) {
    return res.status(400).json({ error: 'Email and password are required.' });
  }
  try {
    const db = req.app.locals.db;
    const user = await getAsync(db, 'SELECT * FROM users WHERE email = ? AND is_active = 1', [email.toLowerCase().trim()]);
    if (!user) {
      return res.status(401).json({ error: 'Invalid email or password.' });
    }
    const valid = bcrypt.compareSync(password, user.password_hash);
    if (!valid) {
      return res.status(401).json({ error: 'Invalid email or password.' });
    }

    // Get employee profile if exists
    const emp = await getAsync(db,
      `SELECT e.*, d.name as department_name
       FROM employees e
       LEFT JOIN departments d ON e.department_id = d.id
       WHERE e.user_id = ?`, [user.id]);

    const expiresIn = ['super_admin', 'hr_manager'].includes(user.role) ? '24h' : '8h';
    const payload = {
      userId: user.id,
      email: user.email,
      role: user.role,
      empId: emp ? emp.id : null,
      name: emp ? `${emp.first_name} ${emp.last_name}` : 'System Administrator',
      avatar: emp ? emp.avatar_url : null,
      roleTitle: emp ? emp.role_title : 'System Administrator',
    };

    const token = jwt.sign(payload, JWT_SECRET, { expiresIn });

    // Update last login
    await runAsync(db, 'UPDATE users SET last_login = datetime("now") WHERE id = ?', [user.id]);

    // Audit log
    await runAsync(db, 'INSERT INTO audit_logs (id, user_id, action, resource, ip_address) VALUES (?,?,?,?,?)',
      [require('uuid').v4(), user.id, 'LOGIN', 'auth', req.ip]);

    res.json({
      token,
      user: {
        ...payload,
        employeeProfile: emp || null,
      }
    });
  } catch (err) {
    console.error('[Auth] Login error:', err);
    res.status(500).json({ error: 'Internal server error.' });
  }
});

// GET /api/auth/me
router.get('/me', verifyToken, async (req, res) => {
  try {
    const db = req.app.locals.db;
    const user = await getAsync(db, 'SELECT id, email, role, last_login, created_at FROM users WHERE id = ?', [req.user.userId]);
    if (!user) return res.status(404).json({ error: 'User not found.' });
    const emp = await getAsync(db,
      `SELECT e.*, d.name as department_name
       FROM employees e
       LEFT JOIN departments d ON e.department_id = d.id
       WHERE e.user_id = ?`, [user.id]);
    res.json({ ...user, employeeProfile: emp || null });
  } catch (err) {
    res.status(500).json({ error: 'Internal server error.' });
  }
});

// POST /api/auth/logout
router.post('/logout', verifyToken, async (req, res) => {
  try {
    const db = req.app.locals.db;
    await runAsync(db, 'INSERT INTO audit_logs (id, user_id, action, resource, ip_address) VALUES (?,?,?,?,?)',
      [require('uuid').v4(), req.user.userId, 'LOGOUT', 'auth', req.ip]);
    res.json({ message: 'Logged out successfully.' });
  } catch (err) {
    res.status(500).json({ error: 'Internal server error.' });
  }
});

module.exports = router;
