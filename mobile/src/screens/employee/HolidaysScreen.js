import React, { useState, useEffect } from "react";
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity, ActivityIndicator, Alert,
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { Ionicons } from "@expo/vector-icons";
import { fetchEmployeeHolidays } from "../../api/client";

const MONTH_NAMES = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

function groupByMonth(holidays) {
  const groups = {};
  holidays.forEach(h => {
    const d = new Date(h.date);
    const key = `${d.getFullYear()}-${d.getMonth()}`;
    const label = `${MONTH_NAMES[d.getMonth()]} ${d.getFullYear()}`;
    if (!groups[key]) groups[key] = { label, items: [] };
    groups[key].items.push(h);
  });
  return Object.values(groups);
}

export default function HolidaysScreen({ navigation }) {
  const [holidays, setHolidays] = useState([]);
  const [loading, setLoading]   = useState(true);
  const currentYear = new Date().getFullYear();
  const [filterYear, setFilterYear] = useState(currentYear);

  useEffect(() => {
    fetchEmployeeHolidays()
      .then(res => { if (res.data.ok) setHolidays(res.data.holidays); })
      .catch(() => Alert.alert("Error", "Failed to load holidays."))
      .finally(() => setLoading(false));
  }, []);

  const filtered = holidays.filter(h => new Date(h.date).getFullYear() === filterYear);
  const groups   = groupByMonth(filtered);
  const upcoming = filtered.filter(h => !h.passed).length;

  return (
    <LinearGradient colors={["#F8FAFC", "#F3F7FD", "#EDF4FF"]} style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
          <Ionicons name="arrow-back" size={22} color="#173B8C" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Holidays</Text>
        <View style={{ width: 40 }} />
      </View>

      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        {/* Year picker */}
        <View style={styles.yearRow}>
          <TouchableOpacity onPress={() => setFilterYear(y => y - 1)} style={styles.yearBtn}>
            <Ionicons name="chevron-back" size={20} color="#173B8C" />
          </TouchableOpacity>
          <Text style={styles.yearLabel}>{filterYear}</Text>
          <TouchableOpacity onPress={() => setFilterYear(y => y + 1)} style={styles.yearBtn}>
            <Ionicons name="chevron-forward" size={20} color="#173B8C" />
          </TouchableOpacity>
        </View>

        {/* Stats */}
        <View style={styles.statsRow}>
          <View style={[styles.statCard, { backgroundColor: "#EEF4FF" }]}>
            <Text style={[styles.statNum, { color: "#173B8C" }]}>{filtered.length}</Text>
            <Text style={[styles.statLabel, { color: "#173B8C" }]}>Total</Text>
          </View>
          <View style={[styles.statCard, { backgroundColor: "#DCFCE7" }]}>
            <Text style={[styles.statNum, { color: "#166534" }]}>{upcoming}</Text>
            <Text style={[styles.statLabel, { color: "#166534" }]}>Upcoming</Text>
          </View>
          <View style={[styles.statCard, { backgroundColor: "#F1F5F9" }]}>
            <Text style={[styles.statNum, { color: "#64748B" }]}>{filtered.length - upcoming}</Text>
            <Text style={[styles.statLabel, { color: "#64748B" }]}>Passed</Text>
          </View>
        </View>

        {loading ? (
          <View style={styles.center}><ActivityIndicator size="large" color="#173B8C" /></View>
        ) : filtered.length === 0 ? (
          <View style={styles.empty}>
            <Ionicons name="calendar-outline" size={48} color="#CBD5E1" />
            <Text style={styles.emptyTxt}>No holidays for {filterYear}</Text>
          </View>
        ) : groups.map(group => (
          <View key={group.label}>
            <Text style={styles.monthHeader}>{group.label}</Text>
            {group.items.map((h, i) => {
              const d = new Date(h.date);
              const dayName = d.toLocaleDateString("en-US", { weekday: "long" });
              const dayNum  = d.getDate();
              return (
                <View key={i} style={[styles.holidayRow, h.passed && styles.passedRow]}>
                  <View style={[styles.dateBubble, h.passed && styles.passedBubble]}>
                    <Text style={[styles.dateBubbleNum, h.passed && styles.passedText]}>{dayNum}</Text>
                    <Text style={[styles.dateBubbleMon, h.passed && styles.passedText]}>
                      {MONTH_NAMES[d.getMonth()]}
                    </Text>
                  </View>
                  <View style={styles.holidayInfo}>
                    <Text style={[styles.holidayName, h.passed && { color: "#94A3B8" }]}>{h.name}</Text>
                    <Text style={styles.holidayDay}>{dayName}</Text>
                  </View>
                  {!h.passed && (
                    <View style={styles.upcomingBadge}>
                      <Text style={styles.upcomingTxt}>Upcoming</Text>
                    </View>
                  )}
                </View>
              );
            })}
          </View>
        ))}
        <View style={{ height: 40 }} />
      </ScrollView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    paddingTop: 55, paddingHorizontal: 20, paddingBottom: 16,
    backgroundColor: "#FFFFFF",
    shadowColor: "#000", shadowOpacity: 0.04, shadowRadius: 8, shadowOffset: { width: 0, height: 2 },
    elevation: 3,
  },
  backBtn:     { width: 40, height: 40, borderRadius: 12, backgroundColor: "#EEF4FF", justifyContent: "center", alignItems: "center" },
  headerTitle: { fontSize: 18, fontWeight: "700", color: "#0F172A" },
  scroll:      { padding: 20 },
  center:      { alignItems: "center", paddingVertical: 60 },
  yearRow:     { flexDirection: "row", alignItems: "center", justifyContent: "center", marginBottom: 16 },
  yearBtn:     { width: 36, height: 36, borderRadius: 10, backgroundColor: "#EEF4FF", justifyContent: "center", alignItems: "center" },
  yearLabel:   { width: 80, textAlign: "center", fontSize: 20, fontWeight: "800", color: "#0F172A" },
  statsRow:    { flexDirection: "row", justifyContent: "space-between", marginBottom: 20 },
  statCard:    { flex: 1, marginHorizontal: 4, borderRadius: 14, padding: 14, alignItems: "center" },
  statNum:     { fontSize: 24, fontWeight: "800" },
  statLabel:   { fontSize: 12, fontWeight: "600", marginTop: 2 },
  monthHeader: { fontSize: 13, fontWeight: "700", color: "#94A3B8", textTransform: "uppercase", letterSpacing: 1, marginBottom: 8, marginTop: 4 },
  holidayRow: {
    flexDirection: "row", alignItems: "center", backgroundColor: "#FFFFFF",
    borderRadius: 16, padding: 14, marginBottom: 8,
    shadowColor: "#000", shadowOpacity: 0.04, shadowRadius: 8, shadowOffset: { width: 0, height: 2 },
    elevation: 2,
  },
  passedRow:       { backgroundColor: "#F8FAFC", shadowOpacity: 0 },
  dateBubble:      { width: 48, height: 52, borderRadius: 14, backgroundColor: "#EEF4FF", alignItems: "center", justifyContent: "center", marginRight: 14 },
  passedBubble:    { backgroundColor: "#F1F5F9" },
  dateBubbleNum:   { fontSize: 18, fontWeight: "800", color: "#173B8C" },
  dateBubbleMon:   { fontSize: 11, fontWeight: "600", color: "#173B8C" },
  passedText:      { color: "#94A3B8" },
  holidayInfo:     { flex: 1 },
  holidayName:     { fontSize: 15, fontWeight: "700", color: "#0F172A" },
  holidayDay:      { fontSize: 12, color: "#94A3B8", marginTop: 2 },
  upcomingBadge:   { backgroundColor: "#DCFCE7", paddingHorizontal: 10, paddingVertical: 5, borderRadius: 20 },
  upcomingTxt:     { fontSize: 11, fontWeight: "700", color: "#166534" },
  empty:           { alignItems: "center", paddingVertical: 50 },
  emptyTxt:        { color: "#94A3B8", fontSize: 15, marginTop: 12 },
});
