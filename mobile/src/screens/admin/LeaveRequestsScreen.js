import React, { useState, useCallback } from 'react';
import {
  View, Text, ScrollView, StyleSheet, RefreshControl,
  TouchableOpacity, Alert, ActivityIndicator,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { useFocusEffect } from '@react-navigation/native';
import { fetchLeaveRequests, leaveAction } from '../../api/client';
import Badge from '../../components/Badge';
import { COLORS } from '../../config';

export default function LeaveRequestsScreen() {
  const [leaves, setLeaves]       = useState([]);
  const [loading, setLoading]     = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [acting, setActing]       = useState(null);

  const load = async () => {
    try {
      const res = await fetchLeaveRequests();
      if (res.data.ok) setLeaves(res.data.leaves);
    } catch (_) {}
    setLoading(false);
    setRefreshing(false);
  };

  useFocusEffect(useCallback(() => { load(); }, []));

  const handle = (lid, action) => {
    Alert.alert(
      action === 'Approved' ? 'Approve Leave' : 'Decline Leave',
      `${action === 'Approved' ? 'Approve' : 'Decline'} this leave request?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: action === 'Approved' ? 'Approve' : 'Decline',
          style: action === 'Approved' ? 'default' : 'destructive',
          onPress: async () => {
            setActing(lid);
            try {
              await leaveAction(lid, action);
              await load();
            } catch (_) {
              Alert.alert('Error', 'Action failed.');
            }
            setActing(null);
          },
        },
      ]
    );
  };

  if (loading) {
    return (
      <LinearGradient colors={COLORS.adminBg} style={styles.center}>
        <ActivityIndicator size="large" color="#fff" />
      </LinearGradient>
    );
  }

  const pending  = leaves.filter(l => l.status === 'Pending');
  const resolved = leaves.filter(l => l.status !== 'Pending');

  return (
    <LinearGradient colors={COLORS.adminBg} style={styles.bg}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(); }} tintColor="#fff" />}
      >
        <Text style={styles.pageTitle}>📋 Leave Requests</Text>
        <Text style={styles.pageSubtitle}>{leaves.length} total · {pending.length} pending</Text>

        {leaves.length === 0 && (
          <View style={styles.emptyBox}>
            <Text style={styles.emptyTxt}>No leave requests yet.</Text>
          </View>
        )}

        {/* Pending */}
        {pending.map(l => (
          <View key={l.id} style={[styles.card, styles.pendingCard]}>
            <View style={styles.cardHeader}>
              <View>
                <Text style={styles.name}>{l.name}</Text>
                <Text style={styles.empId}>{l.employee_id}</Text>
              </View>
              <Badge label={l.status} />
            </View>
            <View style={styles.row}>
              <Text style={styles.lbl}>📅 Date</Text>
              <Text style={styles.val}>{l.leave_date}</Text>
            </View>
            <View style={styles.row}>
              <Text style={styles.lbl}>📝 Reason</Text>
              <Text style={[styles.val, { flex: 1, textAlign: 'right' }]}>{l.reason}</Text>
            </View>
            <View style={styles.row}>
              <Text style={styles.lbl}>🕐 Requested</Text>
              <Text style={styles.val}>{l.requested_at?.slice(0, 10)}</Text>
            </View>
            <View style={styles.actions}>
              <TouchableOpacity
                style={[styles.actionBtn, styles.approveBtn]}
                onPress={() => handle(l.id, 'Approved')}
                disabled={acting === l.id}
              >
                {acting === l.id
                  ? <ActivityIndicator size="small" color="#fff" />
                  : <Text style={styles.actionTxt}>✅ Approve</Text>}
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.actionBtn, styles.declineBtn]}
                onPress={() => handle(l.id, 'Declined')}
                disabled={acting === l.id}
              >
                <Text style={styles.actionTxt}>❌ Decline</Text>
              </TouchableOpacity>
            </View>
          </View>
        ))}

        {/* Resolved */}
        {resolved.map(l => (
          <View key={l.id} style={styles.card}>
            <View style={styles.cardHeader}>
              <View>
                <Text style={styles.name}>{l.name}</Text>
                <Text style={styles.empId}>{l.employee_id}</Text>
              </View>
              <Badge label={l.status} />
            </View>
            <View style={styles.row}>
              <Text style={styles.lbl}>📅 Date</Text>
              <Text style={styles.val}>{l.leave_date}</Text>
            </View>
            <View style={styles.row}>
              <Text style={styles.lbl}>📝 Reason</Text>
              <Text style={[styles.val, { flex: 1, textAlign: 'right' }]}>{l.reason}</Text>
            </View>
          </View>
        ))}
      </ScrollView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  bg:     { flex: 1 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  scroll: { padding: 20, paddingTop: 60 },

  pageTitle:    { color: '#fff', fontSize: 22, fontWeight: '700' },
  pageSubtitle: { color: COLORS.textMuted, fontSize: 13, marginBottom: 20, marginTop: 4 },

  emptyBox: { backgroundColor: COLORS.card, borderRadius: 14, padding: 30, alignItems: 'center', borderWidth: 1, borderColor: COLORS.border },
  emptyTxt: { color: COLORS.textMuted },

  card:        { backgroundColor: COLORS.card, borderRadius: 16, padding: 16, marginBottom: 12, borderWidth: 1, borderColor: COLORS.border },
  pendingCard: { borderColor: 'rgba(251,191,36,0.3)', backgroundColor: 'rgba(251,191,36,0.05)' },

  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 },
  name:   { color: '#fff', fontWeight: '700', fontSize: 15 },
  empId:  { color: COLORS.textMuted, fontSize: 11, marginTop: 2 },

  row:  { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 6 },
  lbl:  { color: COLORS.textMuted, fontSize: 13 },
  val:  { color: '#fff', fontSize: 13 },

  actions:    { flexDirection: 'row', gap: 10, marginTop: 14 },
  actionBtn:  { flex: 1, paddingVertical: 10, borderRadius: 10, alignItems: 'center' },
  approveBtn: { backgroundColor: 'rgba(34,197,94,0.25)', borderWidth: 1, borderColor: 'rgba(34,197,94,0.4)' },
  declineBtn: { backgroundColor: 'rgba(239,68,68,0.20)', borderWidth: 1, borderColor: 'rgba(239,68,68,0.4)' },
  actionTxt:  { color: '#fff', fontWeight: '600', fontSize: 13 },
});
