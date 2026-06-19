import React, { useState, useCallback } from 'react';
import {
  View, Text, ScrollView, StyleSheet, RefreshControl,
  ActivityIndicator,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { useFocusEffect } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import {
  fetchNotifications, markNotificationsRead,
  fetchEmployeeNotifications, markEmployeeNotificationsRead,
} from '../api/client';
import { useAuth } from '../store/AuthContext';
import { COLORS } from '../config';

export default function NotificationsScreen() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading]             = useState(true);
  const [refreshing, setRefreshing]       = useState(false);

  const load = useCallback(async () => {
    try {
      const fetchFn = isAdmin ? fetchNotifications : fetchEmployeeNotifications;
      const res = await fetchFn();
      if (res.data.ok) setNotifications(res.data.notifications);
      const markFn = isAdmin ? markNotificationsRead : markEmployeeNotificationsRead;
      await markFn();
    } catch (_) {}
    setLoading(false);
    setRefreshing(false);
  }, [isAdmin]);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const bgColors = isAdmin ? COLORS.adminBg : COLORS.employeeBg;

  if (loading) {
    return (
      <LinearGradient colors={bgColors} style={styles.center}>
        <ActivityIndicator size="large" color="#fff" />
      </LinearGradient>
    );
  }

  return (
    <LinearGradient colors={bgColors} style={styles.bg}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => { setRefreshing(true); load(); }}
            tintColor="#fff"
          />
        }
      >
        <Text style={styles.pageTitle}>🔔 Notifications</Text>

        {notifications.length === 0 && (
          <View style={styles.emptyCard}>
            <Ionicons name="notifications-off-outline" size={44} color={COLORS.textMuted} />
            <Text style={styles.emptyTitle}>No notifications yet</Text>
            <Text style={styles.emptySubtitle}>
              You'll see leave approvals and other updates here.
            </Text>
          </View>
        )}

        {notifications.map((n) => (
          <View key={n.id} style={[styles.card, !n.is_read && styles.unreadCard]}>
            <View style={styles.cardHeader}>
              <Text style={styles.cardTitle}>{n.title}</Text>
              {!n.is_read && <View style={styles.dot} />}
            </View>
            <Text style={styles.cardMsg}>{n.message}</Text>
            <Text style={styles.cardTime}>{n.created_at}</Text>
          </View>
        ))}
      </ScrollView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  bg:     { flex: 1 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  scroll: { padding: 20, paddingTop: 60, paddingBottom: 30 },

  pageTitle: { fontSize: 22, fontWeight: '700', color: '#fff', marginBottom: 20 },

  emptyCard: {
    alignItems: 'center', justifyContent: 'center',
    backgroundColor: COLORS.card, borderRadius: 16,
    padding: 40, borderWidth: 1, borderColor: COLORS.border,
    marginTop: 20,
  },
  emptyTitle:    { color: '#fff', fontSize: 16, fontWeight: '600', marginTop: 14 },
  emptySubtitle: { color: COLORS.textMuted, fontSize: 13, marginTop: 6, textAlign: 'center' },

  card: {
    backgroundColor: COLORS.card, borderRadius: 14, padding: 14,
    marginBottom: 10, borderWidth: 1, borderColor: COLORS.border,
  },
  unreadCard: {
    borderColor: 'rgba(59,130,246,0.5)',
    backgroundColor: 'rgba(59,130,246,0.08)',
  },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 },
  cardTitle:  { color: '#fff', fontWeight: '700', fontSize: 14, flex: 1 },
  dot: {
    width: 8, height: 8, borderRadius: 4,
    backgroundColor: '#3b82f6', marginLeft: 8,
  },
  cardMsg:  { color: COLORS.textMuted, fontSize: 13, lineHeight: 19 },
  cardTime: { color: COLORS.textDim, fontSize: 11, marginTop: 8 },
});
