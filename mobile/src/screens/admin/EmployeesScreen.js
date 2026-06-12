import React, { useState, useCallback } from 'react';
import {
  View, Text, ScrollView, StyleSheet, RefreshControl,
  TextInput, ActivityIndicator,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { useFocusEffect } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import { fetchEmployees } from '../../api/client';
import { COLORS } from '../../config';

export default function EmployeesScreen() {
  const [employees, setEmployees] = useState([]);
  const [filtered, setFiltered]   = useState([]);
  const [search, setSearch]       = useState('');
  const [loading, setLoading]     = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = async () => {
    try {
      const res = await fetchEmployees();
      if (res.data.ok) {
        setEmployees(res.data.employees);
        setFiltered(res.data.employees);
      }
    } catch (_) {}
    setLoading(false);
    setRefreshing(false);
  };

  useFocusEffect(useCallback(() => { load(); }, []));

  const onSearch = (txt) => {
    setSearch(txt);
    const q = txt.toLowerCase();
    setFiltered(
      employees.filter(e =>
        e.name.toLowerCase().includes(q) ||
        e.employee_id.toLowerCase().includes(q) ||
        (e.email || '').toLowerCase().includes(q)
      )
    );
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
        <Text style={styles.pageTitle}>👥 Employees</Text>
        <Text style={styles.pageSubtitle}>{employees.length} total</Text>

        {/* Search */}
        <View style={styles.searchRow}>
          <Ionicons name="search-outline" size={18} color={COLORS.textMuted} style={{ marginRight: 8 }} />
          <TextInput
            style={styles.searchInput}
            placeholder="Search by name or ID…"
            placeholderTextColor={COLORS.textMuted}
            value={search}
            onChangeText={onSearch}
          />
        </View>

        {filtered.length === 0 && (
          <View style={styles.emptyBox}>
            <Text style={styles.emptyTxt}>No employees found.</Text>
          </View>
        )}

        {filtered.map((emp, idx) => (
          <View key={emp.employee_id} style={styles.card}>
            <View style={styles.avatar}>
              <Text style={styles.avatarTxt}>{emp.name[0]?.toUpperCase()}</Text>
            </View>
            <View style={styles.info}>
              <Text style={styles.name}>{emp.name}</Text>
              <Text style={styles.empId}>{emp.employee_id}</Text>
              {emp.email ? <Text style={styles.email}>{emp.email}</Text> : null}
            </View>
            <View style={styles.salaryBox}>
              {emp.salary_per_day > 0
                ? <Text style={styles.salary}>₹{emp.salary_per_day.toFixed(0)}<Text style={styles.perDay}>/day</Text></Text>
                : <Text style={styles.noSalary}>Not set</Text>}
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
  pageSubtitle: { color: COLORS.textMuted, fontSize: 13, marginBottom: 16, marginTop: 4 },

  searchRow: {
    flexDirection: 'row', alignItems: 'center',
    backgroundColor: COLORS.input, borderRadius: 12,
    paddingHorizontal: 12, marginBottom: 16,
  },
  searchInput: { flex: 1, paddingVertical: 12, color: '#fff', fontSize: 14 },

  emptyBox: { backgroundColor: COLORS.card, borderRadius: 14, padding: 30, alignItems: 'center', borderWidth: 1, borderColor: COLORS.border },
  emptyTxt: { color: COLORS.textMuted },

  card: {
    flexDirection: 'row', alignItems: 'center',
    backgroundColor: COLORS.card, borderRadius: 14,
    padding: 14, marginBottom: 10,
    borderWidth: 1, borderColor: COLORS.border,
  },
  avatar:    { width: 44, height: 44, borderRadius: 22, backgroundColor: 'rgba(99,102,241,0.35)', justifyContent: 'center', alignItems: 'center', marginRight: 12 },
  avatarTxt: { color: '#fff', fontWeight: '700', fontSize: 18 },
  info:      { flex: 1 },
  name:      { color: '#fff', fontWeight: '700', fontSize: 15 },
  empId:     { color: COLORS.textMuted, fontSize: 12, marginTop: 1 },
  email:     { color: COLORS.textDim, fontSize: 11, marginTop: 2 },
  salaryBox: { alignItems: 'flex-end' },
  salary:    { color: COLORS.greenLight, fontWeight: '700', fontSize: 15 },
  perDay:    { color: COLORS.textMuted, fontSize: 11, fontWeight: '400' },
  noSalary:  { color: COLORS.textDim, fontSize: 12, fontStyle: 'italic' },
});
