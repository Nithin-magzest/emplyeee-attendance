import React, { useState, useCallback } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity,
  TextInput, Alert, RefreshControl, ActivityIndicator,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { useFocusEffect } from '@react-navigation/native';
import { fetchAllTickets, ticketAction } from '../../api/client';
import { COLORS } from '../../config';

const STATUSES = ['Open', 'In Progress', 'Resolved', 'Closed'];

const statusColor = (s) => {
  if (s === 'Open')        return '#a5b4fc';
  if (s === 'In Progress') return '#fb923c';
  if (s === 'Resolved')    return '#4ade80';
  return '#9ca3af';
};
const priColor = (p) => {
  if (p === 'High') return '#f87171';
  if (p === 'Low')  return '#9ca3af';
  return '#fbbf24';
};

function TicketCard({ ticket, onUpdate }) {
  const [expanded, setExpanded] = useState(false);
  const [status, setStatus]     = useState(ticket.status);
  const [response, setResponse] = useState(ticket.admin_response || '');
  const [saving, setSaving]     = useState(false);

  const save = async () => {
    setSaving(true);
    try {
      const res = await ticketAction(ticket.id, status, response);
      if (res.data.ok) {
        Alert.alert('Updated', `Ticket #${ticket.id} updated.`);
        onUpdate();
      } else {
        Alert.alert('Error', res.data.msg);
      }
    } catch {
      Alert.alert('Error', 'Network error. Try again.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <View style={[styles.card, { borderLeftColor: priColor(ticket.priority), borderLeftWidth: 4 }]}>
      <TouchableOpacity onPress={() => setExpanded(e => !e)}>
        <View style={styles.cardHeader}>
          <Text style={styles.ticketId}>#{ticket.id}</Text>
          <Text style={styles.ticketSubject}>{ticket.subject}</Text>
          <Text style={[styles.statusText, { color: statusColor(ticket.status) }]}>{ticket.status}</Text>
        </View>
        <Text style={styles.meta}>{ticket.name} ({ticket.employee_id}) · {ticket.category} · {ticket.priority}</Text>
        <Text style={styles.metaDate}>{ticket.created_at?.slice(0, 16)}</Text>
      </TouchableOpacity>

      {expanded && (
        <View style={styles.expandedBody}>
          <Text style={styles.descLabel}>Description</Text>
          <Text style={styles.desc}>{ticket.description}</Text>

          {ticket.admin_response ? (
            <View style={styles.existingResponse}>
              <Text style={styles.existingResponseLabel}>Current Response</Text>
              <Text style={styles.existingResponseText}>{ticket.admin_response}</Text>
            </View>
          ) : null}

          <Text style={styles.fieldLabel}>Update Status</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 12 }}>
            {STATUSES.map(s => (
              <TouchableOpacity
                key={s}
                style={[styles.chip, status === s && styles.chipActive]}
                onPress={() => setStatus(s)}
              >
                <Text style={[styles.chipText, status === s && styles.chipTextActive]}>{s}</Text>
              </TouchableOpacity>
            ))}
          </ScrollView>

          <Text style={styles.fieldLabel}>Response</Text>
          <TextInput
            style={styles.responseInput}
            value={response}
            onChangeText={setResponse}
            placeholder="Write a response to the employee…"
            placeholderTextColor="rgba(255,255,255,0.35)"
            multiline
          />

          <TouchableOpacity style={styles.btnSave} onPress={save} disabled={saving}>
            <Text style={styles.btnSaveText}>{saving ? 'Saving…' : 'Save Update'}</Text>
          </TouchableOpacity>
        </View>
      )}
    </View>
  );
}

export default function AdminTicketsScreen() {
  const [tickets, setTickets]       = useState([]);
  const [loading, setLoading]       = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [filter, setFilter]         = useState('All');

  const load = useCallback(async () => {
    try {
      const res = await fetchAllTickets();
      setTickets(res.data.tickets || []);
    } catch {
      Alert.alert('Error', 'Could not load tickets.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const filtered = filter === 'All'
    ? tickets
    : tickets.filter(t => t.status === filter);

  const open   = tickets.filter(t => t.status === 'Open').length;
  const inprog = tickets.filter(t => t.status === 'In Progress').length;

  if (loading) {
    return (
      <LinearGradient colors={COLORS.adminBg} style={styles.center}>
        <ActivityIndicator size="large" color="#fff" />
      </LinearGradient>
    );
  }

  return (
    <LinearGradient colors={COLORS.adminBg} style={{ flex: 1 }}>
      <ScrollView
        contentContainerStyle={styles.container}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(); }} tintColor="#fff" />}
      >
        <Text style={styles.title}>🎫 Support Tickets</Text>
        <Text style={styles.subtitle}>{open} open · {inprog} in progress · {tickets.length} total</Text>

        {/* Filter tabs */}
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 16 }}>
          {['All', 'Open', 'In Progress', 'Resolved', 'Closed'].map(f => (
            <TouchableOpacity
              key={f}
              style={[styles.filterBtn, filter === f && styles.filterBtnActive]}
              onPress={() => setFilter(f)}
            >
              <Text style={[styles.filterText, filter === f && styles.filterTextActive]}>{f}</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>

        {filtered.length === 0 ? (
          <Text style={styles.empty}>No tickets in this category.</Text>
        ) : (
          filtered.map(t => (
            <TicketCard key={t.id} ticket={t} onUpdate={load} />
          ))
        )}
      </ScrollView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  container: { padding: 20, paddingBottom: 40 },
  title: { color: '#fff', fontSize: 22, fontWeight: '700', marginBottom: 4 },
  subtitle: { color: 'rgba(255,255,255,0.5)', fontSize: 13, marginBottom: 16 },
  filterBtn: {
    paddingHorizontal: 16, paddingVertical: 7, borderRadius: 20, marginRight: 8,
    borderWidth: 1, borderColor: 'rgba(255,255,255,0.25)',
    backgroundColor: 'rgba(255,255,255,0.08)',
  },
  filterBtnActive: { backgroundColor: 'rgba(255,255,255,0.22)', borderColor: 'rgba(255,255,255,0.6)' },
  filterText: { color: 'rgba(255,255,255,0.6)', fontSize: 13 },
  filterTextActive: { color: '#fff', fontWeight: '700' },
  empty: { color: 'rgba(255,255,255,0.4)', textAlign: 'center', marginTop: 40, fontSize: 14 },
  card: {
    backgroundColor: COLORS.card, borderRadius: 14,
    padding: 14, marginBottom: 12,
    borderWidth: 1, borderColor: COLORS.border,
  },
  cardHeader: { flexDirection: 'row', alignItems: 'flex-start', marginBottom: 4 },
  ticketId: { color: 'rgba(255,255,255,0.4)', fontSize: 12, marginRight: 6, paddingTop: 2 },
  ticketSubject: { color: '#fff', fontWeight: '700', fontSize: 14, flex: 1, marginRight: 8 },
  statusText: { fontSize: 12, fontWeight: '700' },
  meta: { color: 'rgba(255,255,255,0.5)', fontSize: 12, marginBottom: 2 },
  metaDate: { color: 'rgba(255,255,255,0.35)', fontSize: 11 },
  expandedBody: { marginTop: 12, borderTopWidth: 1, borderTopColor: 'rgba(255,255,255,0.1)', paddingTop: 12 },
  descLabel: { color: 'rgba(255,255,255,0.55)', fontSize: 11, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.4, marginBottom: 6 },
  desc: { color: 'rgba(255,255,255,0.8)', fontSize: 13, lineHeight: 19, marginBottom: 12 },
  existingResponse: {
    backgroundColor: 'rgba(99,102,241,0.15)', borderRadius: 8, padding: 10,
    borderWidth: 1, borderColor: 'rgba(99,102,241,0.3)', marginBottom: 12,
  },
  existingResponseLabel: { color: '#a5b4fc', fontSize: 11, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.4, marginBottom: 4 },
  existingResponseText: { color: '#c7d2fe', fontSize: 13 },
  fieldLabel: { color: 'rgba(255,255,255,0.55)', fontSize: 11, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.4, marginBottom: 8 },
  chip: {
    paddingHorizontal: 14, paddingVertical: 7, borderRadius: 20,
    borderWidth: 1, borderColor: 'rgba(255,255,255,0.2)',
    backgroundColor: 'rgba(255,255,255,0.07)', marginRight: 8,
  },
  chipActive: { backgroundColor: 'rgba(99,102,241,0.5)', borderColor: '#6366f1' },
  chipText: { color: 'rgba(255,255,255,0.7)', fontSize: 13 },
  chipTextActive: { color: '#fff', fontWeight: '700' },
  responseInput: {
    backgroundColor: 'rgba(255,255,255,0.1)', borderRadius: 9,
    padding: 11, color: '#fff', fontSize: 13,
    minHeight: 80, textAlignVertical: 'top', marginBottom: 12,
  },
  btnSave: {
    backgroundColor: '#6366f1', borderRadius: 10,
    paddingVertical: 12, alignItems: 'center',
  },
  btnSaveText: { color: '#fff', fontWeight: '700', fontSize: 14 },
});
