const jwt = require('jsonwebtoken');
const JWT_SECRET = process.env.JWT_SECRET || 'omnihr_super_secret_jwt_key_2026_enterprise';

function verifyToken(req, res, next) {
  const authHeader = req.headers['authorization'];
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'No token provided. Please login.' });
  }
  const token = authHeader.split(' ')[1];
  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    req.user = decoded;
    next();
  } catch (err) {
    return res.status(401).json({ error: 'Invalid or expired token. Please login again.' });
  }
}

function requireAdmin(req, res, next) {
  if (!req.user || !['super_admin', 'hr_manager'].includes(req.user.role)) {
    return res.status(403).json({ error: 'Access denied. Admin role required.' });
  }
  next();
}

function requireSuperAdmin(req, res, next) {
  if (!req.user || req.user.role !== 'super_admin') {
    return res.status(403).json({ error: 'Access denied. Super Admin role required.' });
  }
  next();
}

module.exports = { verifyToken, requireAdmin, requireSuperAdmin, JWT_SECRET };
