import React, { useState, useCallback } from 'react';
import {
  View, Text, ScrollView, StyleSheet, RefreshControl,
  TouchableOpacity, Alert, ActivityIndicator,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { useFocusEffect } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import { fetchEmployeePortal, employeeCheckin, employeeLogout } from '../../api/client';
import { useAuth } from '../../store/AuthContext';
import Badge from '../../components/Badge';
import { COLORS } from '../../config';

export default function EmployeeDashboard({ navigation }) {
  const { signOut } = useAuth();
  const [data, setData]           = useState(null);
  const [loading, setLoading]     = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [checking, setChecking]   = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);

  const load = async () => {
    try {
      const res = await fetchEmployeePortal();
      if (res.data.ok) {
        setData(res.data);
        setUnreadCount(res.data.unread_notifications ?? 0);
      }
    } catch (e) {
      Alert.alert('Error', 'Failed to load portal.');
    }
    setLoading(false);
    setRefreshing(false);
  };

  useFocusEffect(useCallback(() => { load(); }, []));

  const handleCheckin = async () => {
    setChecking(true);
    try {
      const res = await employeeCheckin();
      if (res.data.ok) {
        Alert.alert(
          res.data.action === 'login' ? '✅ Checked In' : '✅ Checked Out',
          `${res.data.status}\nTime: ${res.data.time}`
        );
        await load();
      } else {
        Alert.alert('Cannot Check In', res.data.msg);
      }
    } catch (e) {
      Alert.alert('Error', e.response?.data?.msg || 'Failed to check in.');
    }
    setChecking(false);
  };

  const handleLogout = async () => {
    try { await employeeLogout(); } catch (_) {}
    signOut();
  };

  const att = data?.today_attendance;
  const checkedIn  = att?.login_time && !att?.logout_time;
  const completed  = att?.login_time && att?.logout_time;

  if (loading) {
    return (
      <LinearGradient colors={COLORS.employeeBg} style={styles.center}>
        <ActivityIndicator size="large" color="#fff" />
      </LinearGradient>
    );
  }

  return (
    <LinearGradient colors={COLORS.employeeBg} style={styles.bg}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(); }} tintColor="#fff" />}
      >
        {/* Header */}
        <View style={styles.header}>
          <View>
            <Text style={styles.greeting}>👋 Hi, {data?.name}</Text>
            <Text style={styles.date}>{data?.today}</Text>
            <Text style={styles.empId}>{data?.employee_id}</Text>
          </View>
          <View style={styles.headerActions}>
            <TouchableOpacity onPress={() => navigation.navigate('Notifications')} style={styles.bellBtn}>
              <Ionicons name="notifications-outline" size={22} color="#fff" />
              {unreadCount > 0 && (
                <View style={styles.badge}>
                  <Text style={styles.badgeText}>{unreadCount > 99 ? '99+' : unreadCount}</Text>
                </View>
              )}
            </TouchableOpacity>
            <TouchableOpacity onPress={handleLogout} style={styles.logoutBtn}>
              <Ionicons name="log-out-outline" size={22} color={COLORS.redLight} />
            </TouchableOpacity>
          </View>
        </View>

        {/* Today's attendance card */}
        <View style={styles.attCard}>
          <Text style={styles.attTitle}>📅 Today's Attendance</Text>
          {att ? (
            <View style={styles.attInfo}>
              <View style={styles.attRow}>
                <Text style={styles.attLbl}>Login</Text>
                <Text style={styles.attVal}>{att.login_time?.slice(0,5) || '–'}</Text>
              </View>
              <View style={styles.attRow}>
                <Text style={styles.attLbl}>Logout</Text>
                <Text style={styles.attVal}>{att.logout_time?.slice(0,5) || '–'}</Text>
              </View>
              <View style={styles.attRow}>
                <Text style={styles.attLbl}>Status</Text>
                <Badge label={att.attendance_type || att.login_status || 'Present'} />
              </View>
            </View>
          ) : (
            <Text style={styles.noAtt}>No attendance recorded today.</Text>
          )}
        </View>

        {/* Check-in / Check-out button */}
        {!completed && (
          <TouchableOpacity
            style={[styles.checkinBtn, checkedIn ? styles.checkoutBtn : styles.checkinBtnColor]}
            onPress={handleCheckin}
            disabled={checking}
          >
            {checking
              ? <ActivityIndicator color="#fff" />
              : <>
                  <Ionicons name={checkedIn ? 'log-out-outline' : 'log-in-outline'} size={22} color="#fff" />
                  <Text style={styles.checkinTxt}>
                    {checkedIn ? 'Check Out' : 'Check In'}
                  </Text>
                </>}
          </TouchableOpacity>
        )}
        {completed && (
          <View style={styles.completedBadge}>
            <Ionicons name="checkmark-circle" size={20} color={COLORS.greenLight} />
            <Text style={styles.completedTxt}>Attendance completed for today</Text>
          </View>
        )}

        {/* Recent attendance */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>📊 Recent Attendance</Text>
          {(!data?.recent_attendance || data.recent_attendance.length === 0) && (
            <Text style={styles.emptyTxt}>No recent records.</Text>
          )}
          {data?.recent_attendance?.map((r, i) => (
            <View key={i} style={styles.recRow}>
              <View>
                <Text style={styles.recDate}>{r.date}</Text>
                <Text style={styles.recTime}>
                  {r.login_time ? r.login_time.slice(0,5) : '–'} {r.logout_time ? `– ${r.logout_time.slice(0,5)}` : ''}
                </Text>
              </View>
              <Badge label={r.attendance_type || (r.login_time ? 'Present' : 'Absent')} />
            </View>
          ))}
        </View>

        {/* Recent leaves */}
        {data?.recent_leaves?.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>📋 Recent Leave Requests</Text>
            {data.recent_leaves.map((l, i) => (
              <View key={i} style={styles.recRow}>
                <View>
                  <Text style={styles.recDate}>{l.leave_date}</Text>
                  <Text style={styles.recTime}>{l.reason}</Text>
                </View>
                <Badge label={l.status} />
              </View>
            ))}
          </View>
        )}
      </ScrollView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  bg:     { flex: 1 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  scroll: { padding: 20, paddingTop: 60 },

  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 },
  greeting: { fontSize: 20, fontWeight: '700', color: '#fff' },
  date:     { fontSize: 13, color: COLORS.textMuted, marginTop: 2 },
  empId:    { fontSize: 12, color: COLORS.textDim, marginTop: 1 },
  headerActions: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  bellBtn:  { padding: 8, backgroundColor: COLORS.card, borderRadius: 10, borderWidth: 1, borderColor: COLORS.border },
  badge:    { position: 'absolute', top: -4, right: -4, backgroundColor: '#ef4444', borderRadius: 8, minWidth: 16, height: 16, justifyContent: 'center', alignItems: 'center', paddingHorizontal: 3 },
  badgeText:{ color: '#fff', fontSize: 9, fontWeight: '700' },
  logoutBtn:{ padding: 8, backgroundColor: COLORS.card, borderRadius: 10, borderWidth: 1, borderColor: COLORS.border },

  attCard: { backgroundColor: COLORS.card, borderRadius: 16, padding: 16, marginBottom: 16, borderWidth: 1, borderColor: COLORS.border },
  attTitle: { color: '#fff', fontWeight: '700', fontSize: 15, marginBottom: 12 },
  attInfo:  {},
  attRow:   { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 7, borderBottomWidth: 1, borderBottomColor: COLORS.border },
  attLbl:   { color: COLORS.textMuted, fontSize: 13 },
  attVal:   { color: '#fff', fontSize: 13, fontWeight: '600' },
  noAtt:    { color: COLORS.textMuted, textAlign: 'center', paddingVertical: 12 },

  checkinBtn:       { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 10, paddingVertical: 16, borderRadius: 14, marginBottom: 16 },
  checkinBtnColor:  { backgroundColor: '#22c55e' },
  checkoutBtn:      { backgroundColor: '#ef4444' },
  checkinTxt:       { color: '#fff', fontWeight: '700', fontSize: 16 },

  completedBadge: { flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: 'rgba(34,197,94,0.1)', borderRadius: 10, padding: 12, marginBottom: 16, borderWidth: 1, borderColor: 'rgba(34,197,94,0.25)' },
  completedTxt:   { color: COLORS.greenLight, fontSize: 13 },

  section:      { backgroundColor: COLORS.card, borderRadius: 16, padding: 16, marginBottom: 14, borderWidth: 1, borderColor: COLORS.border },
  sectionTitle: { color: '#fff', fontWeight: '700', fontSize: 14, marginBottom: 12 },
  emptyTxt:     { color: COLORS.textMuted, textAlign: 'center', paddingVertical: 10 },
  recRow:   { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 9, borderBottomWidth: 1, borderBottomColor: COLORS.border },
  recDate:  { color: '#fff', fontSize: 13, fontWeight: '600' },
  recTime:  { color: COLORS.textMuted, fontSize: 11, marginTop: 2 },
});
