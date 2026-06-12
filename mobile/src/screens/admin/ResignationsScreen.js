import React, { useState, useCallback } from 'react';
import {
  View, Text, ScrollView, StyleSheet, RefreshControl,
  TouchableOpacity, Alert, ActivityIndicator,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { useFocusEffect } from '@react-navigation/native';
import { fetchResignations, resignationAction } from '../../api/client';
import Badge from '../../components/Badge';
import { COLORS } from '../../config';

export default function ResignationsScreen() {
  const [resignations, setResignations] = useState([]);
  const [loading, setLoading]           = useState(true);
  const [refreshing, setRefreshing]     = useState(false);
  const [acting, setActing]             = useState(null);

  const load = async () => {
    try {
      const res = await fetchResignations();
      if (res.data.ok) setResignations(res.data.resignations);
    } catch (_) {}
    setLoading(false);
    setRefreshing(false);
  };

  useFocusEffect(useCallback(() => { load(); }, []));

  const handle = (rid, action) => {
    Alert.alert(
      action === 'Accepted' ? 'Accept Resignation' : 'Decline Resignation',
      `${action === 'Accepted' ? 'Accept' : 'Decline'} this resignation request?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: action,
          style: action === 'Accepted' ? 'default' : 'destructive',
          onPress: async () => {
            setActing(rid);
            try {
              await resignationAction(rid, action);
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

  const pending  = resignations.filter(r => r.status === 'Pending');
  const resolved = resignations.filter(r => r.status !== 'Pending');

  return (
    <LinearGradient colors={COLORS.adminBg} style={styles.bg}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(); }} tintColor="#fff" />}
      >
        <Text style={styles.pageTitle}>📤 Resignations</Text>
        <Text style={styles.pageSubtitle}>{resignations.length} total · {pending.length} pending</Text>

        {resignations.length === 0 && (
          <View style={styles.emptyBox}>
            <Text style={styles.emptyTxt}>No resignation requests.</Text>
          </View>
        )}

        {pending.map(r => (
          <View key={r.id} style={[styles.card, styles.pendingCard]}>
            <View style={styles.cardHeader}>
              <View>
                <Text style={styles.name}>{r.name}</Text>
                <Text style={styles.empId}>{r.employee_id}</Text>
              </View>
              <Badge label={r.status} />
            </View>
            <View style={styles.row}>
              <Text style={styles.lbl}>📅 Last Working Day</Text>
              <Text style={[styles.val, { color: COLORS.redLight }]}>{r.last_working_day}</Text>
            </View>
            <View style={styles.row}>
              <Text style={styles.lbl}>📝 Reason</Text>
              <Text style={[styles.val, { flex: 1, textAlign: 'right' }]}>{r.reason}</Text>
            </View>
            <View style={styles.row}>
              <Text style={styles.lbl}>🕐 Submitted</Text>
              <Text style={styles.val}>{r.requested_at?.slice(0, 10)}</Text>
            </View>
            <View style={styles.actions}>
              <TouchableOpacity
                style={[styles.actionBtn, styles.acceptBtn]}
                onPress={() => handle(r.id, 'Accepted')}
                disabled={acting === r.id}
              >
                {acting === r.id
                  ? <ActivityIndicator size="small" color="#fff" />
                  : <Text style={styles.actionTxt}>✅ Accept</Text>}
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.actionBtn, styles.declineBtn]}
                onPress={() => handle(r.id, 'Declined')}
                disabled={acting === r.id}
              >
                <Text style={styles.actionTxt}>❌ Decline</Text>
              </TouchableOpacity>
            </View>
          </View>
        ))}

        {resolved.map(r => (
          <View key={r.id} style={styles.card}>
            <View style={styles.cardHeader}>
              <View>
                <Text style={styles.name}>{r.name}</Text>
                <Text style={styles.empId}>{r.employee_id}</Text>
              </View>
              <Badge label={r.status} />
            </View>
            <View style={styles.row}>
              <Text style={styles.lbl}>📅 Last Working Day</Text>
              <Text style={styles.val}>{r.last_working_day}</Text>
            </View>
            <View style={styles.row}>
              <Text style={styles.lbl}>📝 Reason</Text>
              <Text style={[styles.val, { flex: 1, textAlign: 'right' }]}>{r.reason}</Text>
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
  pendingCard: { borderColor: 'rgba(239,68,68,0.3)', backgroundColor: 'rgba(239,68,68,0.04)' },

  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 },
  name:   { color: '#fff', fontWeight: '700', fontSize: 15 },
  empId:  { color: COLORS.textMuted, fontSize: 11, marginTop: 2 },

  row:  { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 6 },
  lbl:  { color: COLORS.textMuted, fontSize: 13 },
  val:  { color: '#fff', fontSize: 13 },

  actions:   { flexDirection: 'row', gap: 10, marginTop: 14 },
  actionBtn: { flex: 1, paddingVertical: 10, borderRadius: 10, alignItems: 'center' },
  acceptBtn: { backgroundColor: 'rgba(34,197,94,0.25)', borderWidth: 1, borderColor: 'rgba(34,197,94,0.4)' },
  declineBtn:{ backgroundColor: 'rgba(239,68,68,0.20)', borderWidth: 1, borderColor: 'rgba(239,68,68,0.4)' },
  actionTxt: { color: '#fff', fontWeight: '600', fontSize: 13 },
});
