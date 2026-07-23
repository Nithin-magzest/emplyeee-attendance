import React, { useMemo } from "react";
import {
  View,
  Text,
  StyleSheet,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { Calendar } from "react-native-calendars";

const MONTHS = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

export default function AttendanceCalendar({
  records = [],
  month,
  year,
}) {
  const markedDates = useMemo(() => {
    const marks = {};

    records.forEach((item) => {
      if (!item.date) return;

      let color = "#CBD5E1";

      switch ((item.status || "").toLowerCase()) {
        case "present":
          color = "#22C55E";
          break;

        case "late":
          color = "#F59E0B";
          break;

        case "half day":
        case "halfday":
          color = "#FB923C";
          break;

        case "holiday":
          color = "#8B5CF6";
          break;

        case "absent":
          color = "#EF4444";
          break;
      }

      marks[item.date] = {
        selected: true,
        selectedColor: color,
        selectedTextColor: "#FFFFFF",
      };
    });

    return marks;
  }, [records]);

  return (
    <View style={styles.card}>
      {/* Header */}

      <View style={styles.header}>
        <View style={{ flex: 1 }}>
          <Text style={styles.title}>
            Attendance Calendar
          </Text>

          <Text style={styles.subtitle}>
            Monthly attendance overview
          </Text>
        </View>

        <View style={styles.badge}>
          <Ionicons
            name="calendar-outline"
            size={16}
            color="#173B8C"
          />

          <Text style={styles.badgeText}>
            {MONTHS[month - 1]}
          </Text>
        </View>
      </View>

      <Calendar
        current={`${year}-${String(month).padStart(2, "0")}-01`}
        markedDates={markedDates}
        enableSwipeMonths
        firstDay={1}
        hideExtraDays={false}
        theme={{
          calendarBackground: "#FFFFFF",

          monthTextColor: "#0F172A",
          textMonthFontSize: 20,
          textMonthFontWeight: "800",

          textDayFontSize: 15,
          textDayFontWeight: "700",

          textDayHeaderFontSize: 13,
          textDayHeaderFontWeight: "700",

          textSectionTitleColor: "#94A3B8",

          dayTextColor: "#0F172A",

          todayTextColor: "#173B8C",
          todayBackgroundColor: "#EEF4FF",

          selectedDayTextColor: "#FFFFFF",

          arrowColor: "#173B8C",

          textDisabledColor: "#CBD5E1",

          indicatorColor: "#173B8C",
        }}
        style={styles.calendar}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#FFFFFF",

    borderRadius: 24,

    marginTop: 22,

    borderWidth: 1,
    borderColor: "#E8EDF5",

    shadowColor: "#0F172A",
    shadowOpacity: 0.06,
    shadowRadius: 18,
    shadowOffset: {
      width: 0,
      height: 8,
    },

    elevation: 5,

    overflow: "hidden",
  },

  header: {
    flexDirection: "row",

    alignItems: "center",

    justifyContent: "space-between",

    paddingHorizontal: 22,
    paddingTop: 22,
    paddingBottom: 18,
  },

  title: {
    fontSize: 16,
    fontWeight: "800",
    color: "#0F172A",
  },

  subtitle: {
    marginTop: 4,
    fontSize: 13,
    color: "#64748B",
    fontWeight: "600",
  },

  badge: {
    flexDirection: "row",
    alignItems: "center",

    backgroundColor: "#EEF4FF",

    paddingHorizontal: 12,
    paddingVertical: 8,

    borderRadius: 24,
  },

  badgeText: {
    marginLeft: 6,

    color: "#173B8C",

    fontWeight: "700",

    fontSize: 13,
  },

  calendar: {
    borderTopWidth: 1,
    borderTopColor: "#EEF2F7",

    paddingBottom: 18,
    paddingHorizontal: 6,
  },
});