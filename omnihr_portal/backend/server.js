const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const { initDatabase } = require('./database/init');

const authRoutes = require('./routes/auth');
const employeeRoutes = require('./routes/employees');
const payrollRoutes = require('./routes/payroll');
const attendanceRoutes = require('./routes/attendance');
const performanceRoutes = require('./routes/performance');

const app = express();
const PORT = process.env.PORT || 4000;

// ─── Security Middleware ───────────────────────────────────────────────────────
app.use(helmet({
  crossOriginResourcePolicy: { policy: 'cross-origin' },
  contentSecurityPolicy: false,
}));

app.use(cors({
  origin: ['http://localhost:3000', 'http://localhost:5173', 'http://192.168.20.129:3000', 'http://192.168.20.129:5173'],
  credentials: true,
}));

// Rate limiter for login endpoint: max 10 attempts per 15 minutes
const loginLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 10,
  message: { error: 'Too many login attempts. Please try again in 15 minutes.' },
  standardHeaders: true,
  legacyHeaders: false,
});

// General API rate limiter
const apiLimiter = rateLimit({
  windowMs: 1 * 60 * 1000,
  max: 300,
  message: { error: 'Too many requests. Please slow down.' },
});

app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));
app.use('/api', apiLimiter);

// ─── Routes ───────────────────────────────────────────────────────────────────
app.use('/api/auth/login', loginLimiter);
app.use('/api/auth', authRoutes);
app.use('/api/employees', employeeRoutes);
app.use('/api/payroll', payrollRoutes);
app.use('/api/attendance', attendanceRoutes);
app.use('/api/performance', performanceRoutes);

// Health check
app.get('/api/health', (req, res) => {
  res.json({
    status: 'online',
    version: '1.0.0',
    app: 'OmniHR Premier API',
    timestamp: new Date().toISOString(),
    database: 'SQLite (omnihr.db)',
    uptime: process.uptime().toFixed(1) + 's',
  });
});

// 404 handler
app.use('/api/*', (req, res) => {
  res.status(404).json({ error: `Route ${req.method} ${req.path} not found.` });
});

// ─── Start Server ─────────────────────────────────────────────────────────────
async function start() {
  try {
    console.log('[OmniHR] Starting API server...');
    const db = await initDatabase();
    app.locals.db = db;
    app.listen(PORT, '0.0.0.0', () => {
      console.log(`\n╔══════════════════════════════════════════════════════╗`);
      console.log(`║        OmniHR Premier — API Server                  ║`);
      console.log(`╠══════════════════════════════════════════════════════╣`);
      console.log(`║  Status  : ✅ ONLINE                                 ║`);
      console.log(`║  Port    : http://localhost:${PORT}                   ║`);
      console.log(`║  Database: SQLite (omnihr.db)                        ║`);
      console.log(`║  Health  : http://localhost:${PORT}/api/health        ║`);
      console.log(`╠══════════════════════════════════════════════════════╣`);
      console.log(`║  Demo Credentials:                                   ║`);
      console.log(`║  Admin  : admin@omnihr.io / Admin@123                ║`);
      console.log(`║  HR Mgr : hr@omnihr.io / HRManager@2026              ║`);
      console.log(`║  Emp    : s.martinez@omnihr.io / Employee@123        ║`);
      console.log(`╚══════════════════════════════════════════════════════╝\n`);
    });
  } catch (err) {
    console.error('[OmniHR] Fatal startup error:', err);
    process.exit(1);
  }
}

start();
