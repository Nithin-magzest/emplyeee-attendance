import React, { useState, useCallback } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity,
  Alert, ActivityIndicator, Switch,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { useFocusEffect } from '@react-navigation/native';
import { fetchEmployeePortal, submitResignation } from '../../api/client';
import Badge from '../../components/Badge';
import { COLORS } from '../../config';

const REASONS = [
  '📈 Career Growth',
  '💼 Better Opportunity',
  '🏠 Personal Reasons',
  '🏥 Health Issues',
  '📍 Relocation',
  '✏️ Other',
];

function addDays(n) {
  const d = new Date();
  d.setDate(d.getDate() + n);
  return d.toISOString().split('T')[0];
}

export default function ResignScreen() {
  const [existing, setExisting] = useState(null);
  const [loading, setLoading]   = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const [lastDay, setLastDay]   = useState(addDays(30));
  const [reason, setReason]     = useState('');
  const [confirmed, setConfirmed] = useState(false);

  const load = async () => {
    try {
      const res = await fetchEmployeePortal();
      if (res.data.ok) setExisting(res.data.resignation);
    } catch (_) {}
    setLoading(false);
  };

  useFocusEffect(useCallback(() => { load(); }, []));

  const handleSubmit = () => {
    if (!reason) { Alert.alert('Error', 'Please select a reason.'); return; }
    if (!confirmed) { Alert.alert('Error', 'Please confirm this action.'); return; }

    Alert.alert(
      '⚠️ Confirm Resignation',
      `Last Working Day: ${lastDay}\nReason: ${reason}\n\nThis action cannot be undone. Proceed?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Submit',
          style: 'destructive',
          onPress: async () => {
            setSubmitting(true);
            try {
              const res = await submitResignation(lastDay, reason);
              if (res.data.ok) {
                Alert.alert('Submitted', 'Your resignation has been submitted successfully.');
                await load();
              } else {
                Alert.alert('Error', res.data.msg);
              }
            } catch (e) {
              Alert.alert('Error', e.response?.data?.msg || 'Failed to submit.');
            }
            setSubmitting(false);
          },
        },
      ]
    );
  };

  // Date options: 30 to 90 days from today
  const dateOptions = Array.from({ length: 61 }, (_, i) => addDays(30 + i));

  if (loading) {
    return (
      <LinearGradient colors={COLORS.employeeBg} style={styles.center}>
        <ActivityIndicator size="large" color="#fff" />
      </LinearGradient>
    );
  }

  // Show status if resignation exists and not Declined
  if (existing && existing.status !== 'Declined') {
    return (
      <LinearGradient colors={COLORS.employeeBg} style={styles.bg}>
        <ScrollView contentContainerStyle={styles.scroll}>
          <Text style={styles.pageTitle}>🚨 Resignation Status</Text>

          <View style={[styles.statusCard, existing.status === 'Accepted' ? styles.acceptedCard : styles.pendingCard]}>
            <View style={styles.statusRow}>
              <Text style={styles.lbl}>Status</Text>
              <Badge label={existing.status} />
            </View>
            <View style={styles.statusRow}>
              <Text style={styles.lbl}>Last Working Day</Text>
              <Text style={[styles.val, { color: COLORS.redLight }]}>{existing.last_working_day}</Text>
            </View>
            <View style={styles.statusRow}>
              <Text style={styles.lbl}>Reason</Text>
              <Text style={[styles.val, { flex: 1, textAlign: 'right' }]}>{existing.reason}</Text>
            </View>
            <View style={styles.statusRow}>
              <Text style={styles.lbl}>Submitted</Text>
              <Text style={styles.val}>{existing.created_at?.slice(0, 10)}</Text>
            </View>
          </View>

          {existing.status === 'Pending' && (
            <View style={styles.infoBox}>
              <Text style={styles.infoTxt}>⏳ Your resignation is pending review by the admin.</Text>
            </View>
          )}
          {existing.status === 'Accepted' && (
            <View style={styles.infoBox}>
              <Text style={styles.infoTxt}>✅ Your resignation has been accepted. Please complete the handover process.</Text>
            </View>
          )}
        </ScrollView>
      </LinearGradient>
    );
  }

  return (
    <LinearGradient colors={COLORS.employeeBg} style={styles.bg}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.pageTitle}>🚨 Resign</Text>
        {existing?.status === 'Declined' && (
          <View style={styles.declinedBanner}>
            <Text style={styles.declinedTxt}>❌ Your previous resignation was declined. You may submit a new one.</Text>
          </View>
        )}

        {/* Warning notice */}
        <View style={styles.warnCard}>
          <Text style={styles.warnTitle}>⚠️ Before you proceed:</Text>
          <Text style={styles.warnText}>• A 1-month notice period is required</Text>
          <Text style={styles.warnText}>• Last working day must be at least 30 days from today</Text>
          <Text style={styles.warnText}>• Admin will be notified immediately</Text>
          <Text style={styles.warnText}>• This action cannot be undone</Text>
        </View>

        {/* Last working day */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Last Working Day</Text>
          <Text style={styles.cardSubtitle}>Minimum 30 days from today</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginTop: 12 }}>
            {dateOptions.filter((_, i) => i % 3 === 0).slice(0, 10).map(d => (
              <TouchableOpacity
                key={d}
                style={[styles.dateChip, lastDay === d && styles.dateChipActive]}
                onPress={() => setLastDay(d)}
              >
                <Text style={[styles.dateNum, lastDay === d && styles.dateNumActive]}>
                  {d.split('-')[2]}
                </Text>
                <Text style={[styles.dateMon, lastDay === d && styles.dateMonActive]}>
                  {new Date(d).toLocaleString('default', { month: 'short' })}
                </Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
          <Text style={styles.selectedDate}>Selected: {new Date(lastDay).toDateString()}</Text>
        </View>

        {/* Reason */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Reason for Resignation</Text>
          <View style={styles.chips}>
            {REASONS.map(r => {
              const val = r.replace(/^.+?\s/, '');
              return (
                <TouchableOpacity
                  key={r}
                  style={[styles.chip, reason === val && styles.chipActive]}
                  onPress={() => setReason(val)}
                >
                  <Text style={[styles.chipTxt, reason === val && styles.chipTxtActive]}>{r}</Text>
                </TouchableOpacity>
              );
            })}
          </View>
        </View>

        {/* Confirmation */}
        <View style={styles.confirmRow}>
          <Switch
            value={confirmed}
            onValueChange={setConfirmed}
            trackColor={{ true: '#ef4444', false: 'rgba(255,255,255,0.15)' }}
            thumbColor="#fff"
          />
          <Text style={styles.confirmTxt}>I understand this resignation is official and cannot be undone.</Text>
        </View>

        {/* Submit */}
        <TouchableOpacity
          style={[styles.resignBtn, submitting && styles.disabledBtn]}
          onPress={handleSubmit}
          disabled={submitting}
        >
          {submitting
            ? <ActivityIndicator color="#fff" />
            : <Text style={styles.resignTxt}>📤 Submit Resignation</Text>}
        </TouchableOpacity>
      </ScrollView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  bg:     { flex: 1 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  scroll: { padding: 20, paddingTop: 60, paddingBottom: 40 },

  pageTitle: { color: '#fff', fontSize: 22, fontWeight: '700', marginBottom: 16 },

  declinedBanner: { backgroundColor: 'rgba(239,68,68,0.15)', borderRadius: 12, padding: 14, marginBottom: 16, borderWidth: 1, borderColor: 'rgba(239,68,68,0.3)' },
  declinedTxt:    { color: COLORS.redLight, fontSize: 13 },

  warnCard:  { backgroundColor: 'rgba(239,68,68,0.08)', borderRadius: 14, padding: 16, marginBottom: 16, borderWidth: 1, borderColor: 'rgba(239,68,68,0.25)' },
  warnTitle: { color: '#f87171', fontWeight: '700', marginBottom: 8 },
  warnText:  { color: '#fca5a5', fontSize: 13, marginTop: 3 },

  card:        { backgroundColor: COLORS.card, borderRadius: 16, padding: 16, marginBottom: 14, borderWidth: 1, borderColor: COLORS.border },
  cardTitle:   { color: '#fff', fontWeight: '700', fontSize: 14 },
  cardSubtitle:{ color: COLORS.textMuted, fontSize: 12, marginTop: 2 },

  dateChip:       { width: 54, alignItems: 'center', padding: 10, borderRadius: 12, marginRight: 8, backgroundColor: 'rgba(255,255,255,0.07)', borderWidth: 1, borderColor: COLORS.border },
  dateChipActive: { backgroundColor: 'rgba(239,68,68,0.4)', borderColor: '#ef4444' },
  dateNum:        { color: '#fff', fontWeight: '700', fontSize: 16 },
  dateNumActive:  { color: '#fff' },
  dateMon:        { color: COLORS.textMuted, fontSize: 11, marginTop: 2 },
  dateMonActive:  { color: 'rgba(255,255,255,0.9)' },
  selectedDate:   { color: COLORS.textMuted, fontSize: 12, marginTop: 10 },

  chips:        { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 12 },
  chip:         { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 20, backgroundColor: 'rgba(255,255,255,0.07)', borderWidth: 1, borderColor: COLORS.border },
  chipActive:   { backgroundColor: 'rgba(239,68,68,0.3)', borderColor: '#ef4444' },
  chipTxt:      { color: COLORS.textMuted, fontSize: 13 },
  chipTxtActive:{ color: '#fff', fontWeight: '600' },

  confirmRow: { flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 20, backgroundColor: 'rgba(239,68,68,0.07)', borderRadius: 12, padding: 14, borderWidth: 1, borderColor: 'rgba(239,68,68,0.2)' },
  confirmTxt: { flex: 1, color: COLORS.textMuted, fontSize: 13, lineHeight: 18 },

  resignBtn:    { backgroundColor: '#ef4444', paddingVertical: 15, borderRadius: 14, alignItems: 'center' },
  disabledBtn:  { opacity: 0.6 },
  resignTxt:    { color: '#fff', fontWeight: '700', fontSize: 15 },

  // Status card styles
  statusCard:   { backgroundColor: COLORS.card, borderRadius: 16, padding: 18, marginBottom: 14, borderWidth: 1, borderColor: COLORS.border },
  pendingCard:  { borderColor: 'rgba(251,191,36,0.3)' },
  acceptedCard: { borderColor: 'rgba(34,197,94,0.3)' },
  statusRow:    { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: COLORS.border },
  lbl:          { color: COLORS.textMuted, fontSize: 13 },
  val:          { color: '#fff', fontSize: 13, fontWeight: '600' },
  infoBox:      { backgroundColor: 'rgba(99,102,241,0.1)', borderRadius: 12, padding: 14, borderWidth: 1, borderColor: 'rgba(99,102,241,0.25)' },
  infoTxt:      { color: '#a5b4fc', fontSize: 13, lineHeight: 20 },
});
