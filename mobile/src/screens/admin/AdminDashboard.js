import React, { useState, useCallback } from 'react';
import {
  View, Text, ScrollView, StyleSheet, RefreshControl,
  TouchableOpacity, ActivityIndicator, Alert,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { useFocusEffect } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import { fetchDashboard, adminLogout } from '../../api/client';
import { useAuth } from '../../store/AuthContext';
import StatCard from '../../components/StatCard';
import Badge from '../../components/Badge';
import { COLORS } from '../../config';

export default function AdminDashboard() {
  const { signOut, user } = useAuth();
  const [data, setData]         = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [loading, setLoading]   = useState(true);

  const load = async () => {
    try {
      const res = await fetchDashboard();
      if (res.data.ok) setData(res.data);
    } catch (e) {
      Alert.alert('Error', 'Failed to load dashboard.');
    }
    setLoading(false);
    setRefreshing(false);
  };

  useFocusEffect(useCallback(() => { load(); }, []));

  const handleLogout = async () => {
    try { await adminLogout(); } catch (_) {}
    signOut();
  };

  if (loading) {
    return (
      <LinearGradient colors={COLORS.adminBg} style={styles.center}>
        <ActivityIndicator size="large" color="#fff" />
      </LinearGradient>
    );
  }

  return (
    <LinearGradient colors={COLORS.adminBg} style={styles.bg}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(); }} tintColor="#fff" />}
      >
        {/* Header */}
        <View style={styles.header}>
          <View>
            <Text style={styles.greeting}>👋 Welcome, Admin</Text>
            <Text style={styles.date}>{data?.today || ''}</Text>
          </View>
          <TouchableOpacity onPress={handleLogout} style={styles.logoutBtn}>
            <Ionicons name="log-out-outline" size={22} color={COLORS.redLight} />
          </TouchableOpacity>
        </View>

        {/* Stat cards */}
        <View style={styles.statsRow}>
          <StatCard num={data?.total   ?? '–'} label="👥 Total Employees"  color={COLORS.blueLight}  />
          <StatCard num={data?.present ?? '–'} label="✅ Present Today"     color={COLORS.greenLight} />
        </View>
        <View style={styles.statsRow}>
          <StatCard num={data?.absent  ?? '–'} label="❌ Absent Today"      color={COLORS.redLight}   />
          <StatCard num={data?.late    ?? '–'} label="⏰ Late Today"         color={COLORS.yellowLight}/>
        </View>

        {/* Pending alerts */}
        {(data?.pending_leaves > 0 || data?.pending_resignations > 0) && (
          <View style={styles.alertCard}>
            <Text style={styles.alertTitle}>⚠️ Pending Actions</Text>
            {data.pending_leaves > 0 && (
              <Text style={styles.alertRow}>📋 {data.pending_leaves} leave request{data.pending_leaves > 1 ? 's' : ''} awaiting review</Text>
            )}
            {data.pending_resignations > 0 && (
              <Text style={styles.alertRow}>📤 {data.pending_resignations} resignation{data.pending_resignations > 1 ? 's' : ''} awaiting review</Text>
            )}
          </View>
        )}

        {/* Today's attendance table */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>📅 Today's Attendance</Text>
          {data?.today_rows?.length === 0 && (
            <Text style={styles.empty}>No employees found.</Text>
          )}
          {data?.today_rows?.map((emp) => (
            <View key={emp.employee_id} style={styles.empRow}>
              <View style={styles.empInfo}>
                <Text style={styles.empName}>{emp.name}</Text>
                <Text style={styles.empId}>{emp.employee_id}</Text>
              </View>
              <View style={styles.empRight}>
                <Badge label={emp.attendance_type || (emp.login_time ? 'Present' : 'Absent')} />
                {emp.login_time && (
                  <Text style={styles.time}>
                    {emp.login_time?.slice(0, 5)} {emp.logout_time ? `– ${emp.logout_time.slice(0, 5)}` : ''}
                  </Text>
                )}
              </View>
            </View>
          ))}
        </View>
      </ScrollView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  bg:     { flex: 1 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  scroll: { padding: 20, paddingTop: 60 },

  header: {
    flexDirection: 'row', justifyContent: 'space-between',
    alignItems: 'flex-start', marginBottom: 24,
  },
  greeting:  { fontSize: 20, fontWeight: '700', color: '#fff' },
  date:      { fontSize: 13, color: COLORS.textMuted, marginTop: 2 },
  logoutBtn: { padding: 8, backgroundColor: COLORS.card, borderRadius: 10, borderWidth: 1, borderColor: COLORS.border },

  statsRow: { flexDirection: 'row', marginBottom: 0 },

  alertCard: {
    backgroundColor: 'rgba(251,191,36,0.1)',
    borderWidth: 1, borderColor: 'rgba(251,191,36,0.3)',
    borderRadius: 14, padding: 14, marginTop: 14,
  },
  alertTitle: { color: '#fbbf24', fontWeight: '700', marginBottom: 6 },
  alertRow:   { color: '#fde68a', fontSize: 13, marginTop: 2 },

  section:      { backgroundColor: COLORS.card, borderRadius: 16, padding: 16, marginTop: 16, borderWidth: 1, borderColor: COLORS.border },
  sectionTitle: { color: '#fff', fontWeight: '700', fontSize: 15, marginBottom: 12 },
  empty:        { color: COLORS.textMuted, textAlign: 'center', paddingVertical: 20 },

  empRow:  { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: COLORS.border },
  empInfo: { flex: 1 },
  empName: { color: '#fff', fontSize: 14, fontWeight: '600' },
  empId:   { color: COLORS.textMuted, fontSize: 11, marginTop: 2 },
  empRight:{ alignItems: 'flex-end', gap: 4 },
  time:    { color: COLORS.textDim, fontSize: 11, marginTop: 3 },
});
