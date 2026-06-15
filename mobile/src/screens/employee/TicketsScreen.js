import React, { useState, useCallback } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity,
  TextInput, Alert, RefreshControl, ActivityIndicator,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { useFocusEffect } from '@react-navigation/native';
import { fetchEmployeeTickets, raiseTicket } from '../../api/client';
import { COLORS } from '../../config';

const CATEGORIES = [
  'Work Issue', 'HR Query', 'Salary Query', 'Leave Query',
  'Technical Problem', 'Harassment / Misconduct', 'Facility Issue', 'Other',
];
const PRIORITIES = ['Low', 'Medium', 'High'];

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

export default function TicketsScreen() {
  const [tickets, setTickets]       = useState([]);
  const [loading, setLoading]       = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const [category, setCategory]     = useState('');
  const [priority, setPriority]     = useState('Medium');
  const [subject, setSubject]       = useState('');
  const [description, setDesc]      = useState('');
  const [formOpen, setFormOpen]     = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await fetchEmployeeTickets();
      setTickets(res.data.tickets || []);
    } catch {
      Alert.alert('Error', 'Could not load tickets.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const submit = async () => {
    if (!category) return Alert.alert('Required', 'Please select a category.');
    if (!subject.trim()) return Alert.alert('Required', 'Subject is required.');
    if (!description.trim()) return Alert.alert('Required', 'Description is required.');
    setSubmitting(true);
    try {
      const res = await raiseTicket(category, subject.trim(), description.trim(), priority);
      if (res.data.ok) {
        Alert.alert('Submitted', 'Your ticket has been raised.');
        setCategory(''); setPriority('Medium'); setSubject(''); setDesc('');
        setFormOpen(false);
        load();
      } else {
        Alert.alert('Error', res.data.msg || 'Failed to raise ticket.');
      }
    } catch {
      Alert.alert('Error', 'Network error. Try again.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <LinearGradient colors={COLORS.employeeBg} style={styles.center}>
        <ActivityIndicator size="large" color="#fff" />
      </LinearGradient>
    );
  }

  return (
    <LinearGradient colors={COLORS.employeeBg} style={{ flex: 1 }}>
      <ScrollView
        contentContainerStyle={styles.container}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(); }} tintColor="#fff" />}
      >
        <Text style={styles.title}>🎫 Support Tickets</Text>

        {/* Toggle form */}
        <TouchableOpacity style={styles.btnRaise} onPress={() => setFormOpen(o => !o)}>
          <Text style={styles.btnRaiseText}>{formOpen ? '✕ Cancel' : '+ Raise Ticket'}</Text>
        </TouchableOpacity>

        {/* Raise form */}
        {formOpen && (
          <View style={styles.card}>
            <Text style={styles.sectionLabel}>Category</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 12 }}>
              {CATEGORIES.map(c => (
                <TouchableOpacity
                  key={c}
                  style={[styles.chip, category === c && styles.chipActive]}
                  onPress={() => setCategory(c)}
                >
                  <Text style={[styles.chipText, category === c && styles.chipTextActive]}>{c}</Text>
                </TouchableOpacity>
              ))}
            </ScrollView>

            <Text style={styles.sectionLabel}>Priority</Text>
            <View style={styles.row}>
              {PRIORITIES.map(p => (
                <TouchableOpacity
                  key={p}
                  style={[styles.chip, priority === p && styles.chipActive]}
                  onPress={() => setPriority(p)}
                >
                  <Text style={[styles.chipText, priority === p && styles.chipTextActive]}>{p}</Text>
                </TouchableOpacity>
              ))}
            </View>

            <Text style={styles.sectionLabel}>Subject</Text>
            <TextInput
              style={styles.input}
              placeholder="Brief summary…"
              placeholderTextColor="rgba(255,255,255,0.4)"
              value={subject}
              onChangeText={setSubject}
              maxLength={255}
            />

            <Text style={styles.sectionLabel}>Description</Text>
            <TextInput
              style={[styles.input, { height: 90, textAlignVertical: 'top' }]}
              placeholder="Describe the issue in detail…"
              placeholderTextColor="rgba(255,255,255,0.4)"
              value={description}
              onChangeText={setDesc}
              multiline
            />

            <TouchableOpacity style={styles.btnSubmit} onPress={submit} disabled={submitting}>
              <Text style={styles.btnSubmitText}>{submitting ? 'Submitting…' : '🎫 Submit Ticket'}</Text>
            </TouchableOpacity>
          </View>
        )}

        {/* Ticket list */}
        {tickets.length === 0 ? (
          <Text style={styles.empty}>No tickets raised yet.</Text>
        ) : (
          tickets.map(t => (
            <View key={t.id} style={[styles.card, { borderLeftColor: priColor(t.priority), borderLeftWidth: 4 }]}>
              <View style={styles.ticketHeader}>
                <Text style={styles.ticketSubject}>{t.subject}</Text>
                <Text style={[styles.statusBadge, { color: statusColor(t.status) }]}>{t.status}</Text>
              </View>
              <Text style={styles.ticketMeta}>{t.category} · {t.priority} · {t.created_at?.slice(0, 10)}</Text>
              {t.admin_response ? (
                <View style={styles.response}>
                  <Text style={styles.responseLabel}>Admin Response</Text>
                  <Text style={styles.responseText}>{t.admin_response}</Text>
                </View>
              ) : null}
            </View>
          ))
        )}
      </ScrollView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  container: { padding: 20, paddingBottom: 40 },
  title: { color: '#fff', fontSize: 22, fontWeight: '700', marginBottom: 16 },
  btnRaise: {
    backgroundColor: 'rgba(99,102,241,0.3)',
    borderRadius: 10, paddingVertical: 12,
    alignItems: 'center', marginBottom: 16,
    borderWidth: 1, borderColor: 'rgba(99,102,241,0.5)',
  },
  btnRaiseText: { color: '#a5b4fc', fontWeight: '700', fontSize: 15 },
  card: {
    backgroundColor: COLORS.card,
    borderRadius: 14, padding: 16, marginBottom: 12,
    borderWidth: 1, borderColor: COLORS.border,
  },
  sectionLabel: { color: 'rgba(255,255,255,0.6)', fontSize: 11, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 8 },
  row: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 12 },
  chip: {
    paddingHorizontal: 14, paddingVertical: 7, borderRadius: 20,
    borderWidth: 1, borderColor: 'rgba(255,255,255,0.2)',
    backgroundColor: 'rgba(255,255,255,0.07)', marginRight: 8, marginBottom: 8,
  },
  chipActive: { backgroundColor: 'rgba(99,102,241,0.5)', borderColor: '#6366f1' },
  chipText: { color: 'rgba(255,255,255,0.7)', fontSize: 13 },
  chipTextActive: { color: '#fff', fontWeight: '700' },
  input: {
    backgroundColor: 'rgba(255,255,255,0.12)',
    borderRadius: 9, padding: 11, color: '#fff', fontSize: 14, marginBottom: 12,
  },
  btnSubmit: {
    backgroundColor: '#6366f1', borderRadius: 10,
    paddingVertical: 13, alignItems: 'center', marginTop: 4,
  },
  btnSubmitText: { color: '#fff', fontWeight: '700', fontSize: 15 },
  empty: { color: 'rgba(255,255,255,0.4)', textAlign: 'center', marginTop: 40, fontSize: 14 },
  ticketHeader: { flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 4 },
  ticketSubject: { color: '#fff', fontWeight: '700', fontSize: 14, flex: 1, marginRight: 8 },
  statusBadge: { fontSize: 12, fontWeight: '700' },
  ticketMeta: { color: 'rgba(255,255,255,0.45)', fontSize: 12, marginBottom: 8 },
  response: {
    backgroundColor: 'rgba(99,102,241,0.15)',
    borderRadius: 8, padding: 10,
    borderWidth: 1, borderColor: 'rgba(99,102,241,0.3)',
  },
  responseLabel: { color: '#a5b4fc', fontSize: 11, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.4, marginBottom: 4 },
  responseText: { color: '#c7d2fe', fontSize: 13, lineHeight: 19 },
});
