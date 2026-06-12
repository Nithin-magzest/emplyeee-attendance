import React, { useState } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity,
  Alert, ActivityIndicator, Platform,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { submitLeaveRequest } from '../../api/client';
import { COLORS } from '../../config';

const REASONS = [
  { label: '🤒 Sick Leave',        value: 'Sick Leave' },
  { label: '🏠 Personal Work',     value: 'Personal Work' },
  { label: '👨‍👩‍👦 Family Emergency',   value: 'Family Emergency' },
  { label: '✈️ Travel',            value: 'Travel' },
  { label: '📅 Planned Leave',     value: 'Planned Leave' },
  { label: '✏️ Other',             value: null },
];

function toISODate(date) {
  const d = new Date(date);
  return d.toISOString().split('T')[0];
}

function addDays(days) {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d;
}

export default function LeaveScreen() {
  const tomorrow    = addDays(1);
  const [leaveDate, setLeaveDate] = useState(toISODate(tomorrow));
  const [reason, setReason]       = useState('');
  const [custom, setCustom]       = useState('');
  const [loading, setLoading]     = useState(false);
  const [success, setSuccess]     = useState(false);

  const handleSubmit = async () => {
    const finalReason = reason === null ? custom.trim() : reason;
    if (!finalReason) {
      Alert.alert('Error', 'Please select or enter a reason.');
      return;
    }
    Alert.alert(
      'Submit Leave Request',
      `Date: ${leaveDate}\nReason: ${finalReason}\n\nSubmit this leave request?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Submit',
          onPress: async () => {
            setLoading(true);
            try {
              const res = await submitLeaveRequest(leaveDate, finalReason);
              if (res.data.ok) {
                setSuccess(true);
                setReason('');
                setCustom('');
                setTimeout(() => setSuccess(false), 3000);
              } else {
                Alert.alert('Error', res.data.msg || 'Failed to submit.');
              }
            } catch (e) {
              Alert.alert('Error', e.response?.data?.msg || 'Failed to connect.');
            }
            setLoading(false);
          },
        },
      ]
    );
  };

  // Simple date picker — show next 30 days as scrollable list
  const dateOptions = Array.from({ length: 30 }, (_, i) => {
    const d = addDays(i + 1);
    return { label: d.toDateString(), value: toISODate(d) };
  });

  return (
    <LinearGradient colors={COLORS.employeeBg} style={styles.bg}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.pageTitle}>📋 Request Leave</Text>
        <Text style={styles.pageSubtitle}>Submit a leave request for admin approval</Text>

        {success && (
          <View style={styles.successBanner}>
            <Text style={styles.successTxt}>✅ Leave request submitted successfully!</Text>
          </View>
        )}

        {/* Date selection */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Select Date</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.dateScroll}>
            {dateOptions.slice(0, 14).map(opt => (
              <TouchableOpacity
                key={opt.value}
                style={[styles.dateChip, leaveDate === opt.value && styles.dateChipActive]}
                onPress={() => setLeaveDate(opt.value)}
              >
                <Text style={[styles.dateNum, leaveDate === opt.value && styles.dateNumActive]}>
                  {opt.value.split('-')[2]}
                </Text>
                <Text style={[styles.dateMon, leaveDate === opt.value && styles.dateMonActive]}>
                  {new Date(opt.value).toLocaleString('default', { month: 'short' })}
                </Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
          <Text style={styles.selectedDate}>Selected: {new Date(leaveDate).toDateString()}</Text>
        </View>

        {/* Reason selection */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Reason</Text>
          <View style={styles.chips}>
            {REASONS.map(r => (
              <TouchableOpacity
                key={r.label}
                style={[styles.chip, reason === r.value && styles.chipActive]}
                onPress={() => { setReason(r.value); setCustom(''); }}
              >
                <Text style={[styles.chipTxt, reason === r.value && styles.chipTxtActive]}>
                  {r.label}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          {reason === null && (
            <View style={styles.customInput}>
              <Text style={styles.customLabel}>Describe your reason:</Text>
              <View style={styles.textareaWrap}>
                <Text
                  style={[styles.textarea, !custom && styles.textareaPlaceholder]}
                  onPress={() => {}}
                >
                  {custom || 'Type your reason here…'}
                </Text>
              </View>
            </View>
          )}
        </View>

        {/* Submit */}
        <TouchableOpacity
          style={[styles.submitBtn, loading && styles.submitBtnDisabled]}
          onPress={handleSubmit}
          disabled={loading}
        >
          {loading
            ? <ActivityIndicator color="#fff" />
            : <Text style={styles.submitTxt}>📤 Submit Leave Request</Text>}
        </TouchableOpacity>
      </ScrollView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  bg:     { flex: 1 },
  scroll: { padding: 20, paddingTop: 60 },

  pageTitle:    { color: '#fff', fontSize: 22, fontWeight: '700' },
  pageSubtitle: { color: COLORS.textMuted, fontSize: 13, marginBottom: 20, marginTop: 4 },

  successBanner: { backgroundColor: 'rgba(34,197,94,0.15)', borderRadius: 12, padding: 14, marginBottom: 16, borderWidth: 1, borderColor: 'rgba(34,197,94,0.3)' },
  successTxt:    { color: COLORS.greenLight, fontWeight: '600', textAlign: 'center' },

  card:      { backgroundColor: COLORS.card, borderRadius: 16, padding: 16, marginBottom: 14, borderWidth: 1, borderColor: COLORS.border },
  cardTitle: { color: '#fff', fontWeight: '700', fontSize: 14, marginBottom: 12 },

  dateScroll: { flexDirection: 'row' },
  dateChip:   { width: 52, alignItems: 'center', padding: 10, borderRadius: 12, marginRight: 8, backgroundColor: 'rgba(255,255,255,0.07)', borderWidth: 1, borderColor: COLORS.border },
  dateChipActive: { backgroundColor: 'rgba(99,102,241,0.5)', borderColor: '#6366f1' },
  dateNum:    { color: '#fff', fontWeight: '700', fontSize: 16 },
  dateNumActive: { color: '#fff' },
  dateMon:    { color: COLORS.textMuted, fontSize: 11, marginTop: 2 },
  dateMonActive: { color: 'rgba(255,255,255,0.9)' },
  selectedDate: { color: COLORS.textMuted, fontSize: 12, marginTop: 10 },

  chips:    { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  chip:     { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 20, backgroundColor: 'rgba(255,255,255,0.07)', borderWidth: 1, borderColor: COLORS.border },
  chipActive:   { backgroundColor: 'rgba(99,102,241,0.4)', borderColor: '#6366f1' },
  chipTxt:      { color: COLORS.textMuted, fontSize: 13 },
  chipTxtActive:{ color: '#fff', fontWeight: '600' },

  customInput:    { marginTop: 14 },
  customLabel:    { color: COLORS.textMuted, fontSize: 12, marginBottom: 8 },
  textareaWrap:   { backgroundColor: COLORS.input, borderRadius: 10, padding: 12, minHeight: 80 },
  textarea:       { color: '#fff', fontSize: 14 },
  textareaPlaceholder: { color: COLORS.textMuted },

  submitBtn:         { backgroundColor: '#6366f1', paddingVertical: 15, borderRadius: 14, alignItems: 'center', marginTop: 4 },
  submitBtnDisabled: { opacity: 0.6 },
  submitTxt:         { color: '#fff', fontWeight: '700', fontSize: 15 },
});
