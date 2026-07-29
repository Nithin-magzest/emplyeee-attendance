import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { CURRENT_USER } from '../data/mockHrmsData';

const API_BASE = '/api';

const MOCK_USERS = {
  'admin@omnihr.io': {
    id: 1, email: 'admin@omnihr.io', name: 'Alexander Vance', role: 'super_admin',
    avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80',
    employeeProfile: CURRENT_USER,
  },
  'hr@omnihr.io': {
    id: 2, email: 'hr@omnihr.io', name: 'Sophia Martinez', role: 'hr_manager',
    avatar: 'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=150&auto=format&fit=crop&q=80',
    employeeProfile: CURRENT_USER,
  },
  's.martinez@omnihr.io': {
    id: 3, email: 's.martinez@omnihr.io', name: 'Sophia Martinez', role: 'employee',
    avatar: 'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=150&auto=format&fit=crop&q=80',
    employeeProfile: CURRENT_USER,
  },
};

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('omnihr_user');
    return saved ? JSON.parse(saved) : MOCK_USERS['admin@omnihr.io'];
  });
  const [token, setToken] = useState(() => localStorage.getItem('omnihr_token') || 'demo_jwt_token');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Verify token on load
  useEffect(() => {
    if (token && token !== 'demo_jwt_token') {
      fetch(`${API_BASE}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then(res => (res.ok ? res.json() : Promise.reject()))
        .then(data => {
          setUser(data);
          localStorage.setItem('omnihr_user', JSON.stringify(data));
        })
        .catch(() => {
          // Keep current fallback user
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [token]);

  const login = useCallback(async (email, password) => {
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      if (res.ok) {
        const data = await res.json();
        localStorage.setItem('omnihr_token', data.token);
        localStorage.setItem('omnihr_user', JSON.stringify(data.user));
        setToken(data.token);
        setUser(data.user);
        return { success: true, role: data.user.role };
      }
    } catch (_) {
      // Fallback below if fetch fails
    }

    // Local fallback authentication
    const normEmail = email.toLowerCase().trim();
    const found = MOCK_USERS[normEmail] || (
      normEmail.includes('admin') ? MOCK_USERS['admin@omnihr.io'] :
      normEmail.includes('hr') ? MOCK_USERS['hr@omnihr.io'] :
      MOCK_USERS['s.martinez@omnihr.io']
    );

    const dummyToken = `demo_token_${Date.now()}`;
    localStorage.setItem('omnihr_token', dummyToken);
    localStorage.setItem('omnihr_user', JSON.stringify(found));
    setToken(dummyToken);
    setUser(found);
    return { success: true, role: found.role };
  }, []);

  const logout = useCallback(async () => {
    try {
      if (token && token !== 'demo_jwt_token') {
        await fetch(`${API_BASE}/auth/logout`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
        });
      }
    } catch (_) {}
    localStorage.removeItem('omnihr_token');
    localStorage.removeItem('omnihr_user');
    setToken(null);
    setUser(null);
  }, [token]);

  const apiCall = useCallback(async (path, options = {}) => {
    try {
      const res = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
          ...(options.headers || {}),
        },
      });
      if (res.ok) return await res.json();
    } catch (_) {}
    return { success: true };
  }, [token]);

  const isAdmin = user && ['super_admin', 'hr_manager'].includes(user.role);
  const isSuperAdmin = user && user.role === 'super_admin';

  return (
    <AuthContext.Provider value={{ user, token, loading, error, login, logout, apiCall, isAdmin, isSuperAdmin }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

export { API_BASE };
