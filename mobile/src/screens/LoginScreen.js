import React, { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  ActivityIndicator, Alert, ScrollView, KeyboardAvoidingView, Platform,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { adminLogin, employeeLogin } from '../api/client';
import { useAuth } from '../store/AuthContext';
import { COLORS } from '../config';
import QRScannerModal from './QRScannerModal';

export default function LoginScreen() {
  const { signIn } = useAuth();
  const [tab, setTab]           = useState('admin'); // 'admin' | 'employee'
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [empId, setEmpId]       = useState('');
  const [loading, setLoading]   = useState(false);
  const [showPass, setShowPass] = useState(false);
  const [showScanner, setShowScanner] = useState(false);

  const handleAdminLogin = async () => {
    if (!username.trim() || !password.trim()) {
      Alert.alert('Error', 'Please enter username and password.');
      return;
    }
    setLoading(true);
    try {
      const res = await adminLogin(username.trim(), password.trim());
      if (res.data.ok) {
        await signIn(res.data.token, { role: 'admin', name: res.data.username });
      } else {
        Alert.alert('Login Failed', res.data.msg || 'Invalid credentials.');
      }
    } catch (e) {
      Alert.alert('Error', e.response?.data?.msg || 'Cannot connect to server.');
    }
    setLoading(false);
  };

  const handleEmployeeLogin = async () => {
    if (!empId.trim()) {
      Alert.alert('Error', 'Please enter your Employee ID.');
      return;
    }
    setLoading(true);
    try {
      const res = await employeeLogin(empId.trim());
      if (res.data.ok) {
        await signIn(res.data.token, {
          role: 'employee',
          name: res.data.name,
          employeeId: res.data.employee_id,
        });
      } else {
        Alert.alert('Login Failed', res.data.msg || 'Employee not found.');
      }
    } catch (e) {
      Alert.alert('Error', e.response?.data?.msg || 'Cannot connect to server.');
    }
    setLoading(false);
  };

  return (
    <LinearGradient colors={['#0f2027', '#203a43', '#2c5364']} style={styles.bg}>
      <QRScannerModal visible={showScanner} onClose={() => setShowScanner(false)} />
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">

          {/* Header */}
          <View style={styles.header}>
            <Text style={styles.logo}>⚙️</Text>
            <Text style={styles.title}>Employee Attendance</Text>
            <Text style={styles.subtitle}>Sign in to continue</Text>
          </View>

          {/* Tab switcher */}
          <View style={styles.tabs}>
            <TouchableOpacity
              style={[styles.tab, tab === 'admin' && styles.tabActive]}
              onPress={() => setTab('admin')}
            >
              <Ionicons name="shield-outline" size={16} color={tab === 'admin' ? '#fff' : COLORS.textMuted} />
              <Text style={[styles.tabTxt, tab === 'admin' && styles.tabTxtActive]}>Admin</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.tab, tab === 'employee' && styles.tabActiveEmp]}
              onPress={() => setTab('employee')}
            >
              <Ionicons name="person-outline" size={16} color={tab === 'employee' ? '#fff' : COLORS.textMuted} />
              <Text style={[styles.tabTxt, tab === 'employee' && styles.tabTxtActive]}>Employee</Text>
            </TouchableOpacity>
          </View>

          {/* Card */}
          <View style={styles.card}>
            {tab === 'admin' ? (
              <>
                <Text style={styles.cardTitle}>🔐 Admin Login</Text>

                <Text style={styles.label}>Username</Text>
                <View style={styles.inputRow}>
                  <Ionicons name="person-outline" size={18} color={COLORS.textMuted} style={styles.icon} />
                  <TextInput
                    style={styles.input}
                    placeholder="admin"
                    placeholderTextColor={COLORS.textMuted}
                    value={username}
                    onChangeText={setUsername}
                    autoCapitalize="none"
                  />
                </View>

                <Text style={styles.label}>Password</Text>
                <View style={styles.inputRow}>
                  <Ionicons name="lock-closed-outline" size={18} color={COLORS.textMuted} style={styles.icon} />
                  <TextInput
                    style={[styles.input, { flex: 1 }]}
                    placeholder="••••••••"
                    placeholderTextColor={COLORS.textMuted}
                    value={password}
                    onChangeText={setPassword}
                    secureTextEntry={!showPass}
                  />
                  <TouchableOpacity onPress={() => setShowPass(!showPass)} style={styles.eyeBtn}>
                    <Ionicons name={showPass ? 'eye-off-outline' : 'eye-outline'} size={18} color={COLORS.textMuted} />
                  </TouchableOpacity>
                </View>

                <TouchableOpacity
                  style={[styles.btn, styles.btnAdmin]}
                  onPress={handleAdminLogin}
                  disabled={loading}
                >
                  {loading
                    ? <ActivityIndicator color="#fff" />
                    : <Text style={styles.btnTxt}>Sign In as Admin</Text>}
                </TouchableOpacity>
              </>
            ) : (
              <>
                <Text style={styles.cardTitle}>👤 Employee Login</Text>

                <Text style={styles.label}>Employee ID</Text>
                <View style={styles.inputRow}>
                  <Ionicons name="id-card-outline" size={18} color={COLORS.textMuted} style={styles.icon} />
                  <TextInput
                    style={styles.input}
                    placeholder="e.g. 22HU1A0559"
                    placeholderTextColor={COLORS.textMuted}
                    value={empId}
                    onChangeText={setEmpId}
                    autoCapitalize="characters"
                  />
                </View>

                <TouchableOpacity
                  style={[styles.btn, styles.btnEmployee]}
                  onPress={handleEmployeeLogin}
                  disabled={loading}
                >
                  {loading
                    ? <ActivityIndicator color="#fff" />
                    : <Text style={styles.btnTxt}>Sign In as Employee</Text>}
                </TouchableOpacity>

                {/* Divider */}
                <View style={styles.dividerRow}>
                  <View style={styles.dividerLine} />
                  <Text style={styles.dividerTxt}>or</Text>
                  <View style={styles.dividerLine} />
                </View>

                {/* QR Scan Button */}
                <TouchableOpacity
                  style={styles.scanBtn}
                  onPress={() => setShowScanner(true)}
                >
                  <Ionicons name="qr-code-outline" size={20} color="#fff" />
                  <Text style={styles.scanBtnTxt}>Scan QR Code to Check In</Text>
                </TouchableOpacity>
              </>
            )}
          </View>

        </ScrollView>
      </KeyboardAvoidingView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  bg:       { flex: 1 },
  scroll:   { flexGrow: 1, justifyContent: 'center', padding: 24 },
  header:   { alignItems: 'center', marginBottom: 32 },
  logo:     { fontSize: 48, marginBottom: 10 },
  title:    { fontSize: 24, fontWeight: '700', color: '#fff' },
  subtitle: { fontSize: 13, color: COLORS.textMuted, marginTop: 4 },

  tabs: {
    flexDirection: 'row', marginBottom: 16,
    backgroundColor: 'rgba(0,0,0,0.3)', borderRadius: 14,
    padding: 4,
  },
  tab: {
    flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: 6, paddingVertical: 10, borderRadius: 10,
  },
  tabActive:    { backgroundColor: 'rgba(239,68,68,0.35)' },
  tabActiveEmp: { backgroundColor: 'rgba(99,102,241,0.35)' },
  tabTxt:       { color: COLORS.textMuted, fontSize: 14 },
  tabTxtActive: { color: '#fff', fontWeight: '600' },

  card: {
    backgroundColor: COLORS.card,
    borderRadius: 20,
    padding: 24,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  cardTitle: { fontSize: 18, fontWeight: '700', color: '#fff', marginBottom: 20 },

  label:    { fontSize: 12, color: COLORS.textMuted, marginBottom: 6, textTransform: 'uppercase', letterSpacing: 0.5 },
  inputRow: {
    flexDirection: 'row', alignItems: 'center',
    backgroundColor: COLORS.input,
    borderRadius: 12, marginBottom: 16, paddingHorizontal: 12,
  },
  icon:  { marginRight: 8 },
  input: { flex: 1, paddingVertical: 13, color: '#fff', fontSize: 14 },
  eyeBtn: { padding: 4 },

  btn:         { paddingVertical: 14, borderRadius: 12, alignItems: 'center', marginTop: 8 },
  btnAdmin:    { backgroundColor: '#ef4444' },
  btnEmployee: { backgroundColor: '#6366f1' },
  btnTxt:      { color: '#fff', fontWeight: '700', fontSize: 15 },

  dividerRow: {
    flexDirection: 'row', alignItems: 'center', gap: 10, marginVertical: 16,
  },
  dividerLine: { flex: 1, height: 1, backgroundColor: 'rgba(255,255,255,0.15)' },
  dividerTxt:  { color: COLORS.textMuted, fontSize: 12 },

  scanBtn: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: 10, paddingVertical: 14, borderRadius: 12,
    backgroundColor: 'rgba(99,102,241,0.25)',
    borderWidth: 1, borderColor: 'rgba(99,102,241,0.5)',
  },
  scanBtnTxt: { color: '#fff', fontWeight: '600', fontSize: 15 },
});
