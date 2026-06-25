import React, { useMemo } from "react";
import {
  View,
  Text,
  StyleSheet,
} from "react-native";
import { Calendar } from "react-native-calendars";

export default function AttendanceCalendar({
  records = [],
  month,
  year,
}) {
  const markedDates = useMemo(() => {
    const marks = {};

    records.forEach((item) => {
      if (!item.date) return;

      let color = "#22C55E";

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

        default:
          color = "#CBD5E1";
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
      <View style={styles.header}>
        <Text style={styles.title}>
          Attendance Calendar
        </Text>

        <Text style={styles.subtitle}>
          Monthly Attendance Overview
        </Text>
      </View>

      <Calendar
        current={`${year}-${String(month).padStart(2, "0")}-01`}
        markedDates={markedDates}
        enableSwipeMonths
        firstDay={1}
        hideExtraDays={false}
        theme={{
          calendarBackground: "#FFFFFF",

          monthTextColor: "#173B8C",
          textMonthFontWeight: "800",
          textMonthFontSize: 18,

          textDayFontSize: 15,
          textDayFontWeight: "700",

          textDayHeaderFontWeight: "700",
          textDayHeaderFontSize: 13,

          textSectionTitleColor: "#94A3B8",

          dayTextColor: "#0F172A",

          todayTextColor: "#173B8C",

          selectedDayTextColor: "#FFFFFF",

          arrowColor: "#173B8C",

          textDisabledColor: "#D1D5DB",
        }}
        style={styles.calendar}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#FFFFFF",

    borderRadius: 26,

    marginTop: 22,

    overflow: "hidden",

    shadowColor: "#000",
    shadowOpacity: 0.06,
    shadowRadius: 14,
    shadowOffset: {
      width: 0,
      height: 6,
    },

    elevation: 5,
  },

  header: {
    paddingHorizontal: 22,
    paddingTop: 22,
    paddingBottom: 12,
  },

  title: {
    fontSize: 20,
    fontWeight: "800",
    color: "#0F172A",
  },

  subtitle: {
    marginTop: 4,
    color: "#64748B",
    fontSize: 13,
    fontWeight: "600",
  },

  calendar: {
    paddingBottom: 18,
  },
});