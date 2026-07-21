import React from "react";
import {
  View,
 Text,
  TouchableOpacity,
  StyleSheet,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

import LEAVE_THEME from "../../constants/leaveTheme";

export default function LeaveHeader({
  month,
  year,
  onCalendarPress,
}) {
  return (
    <View style={styles.container}>

      <View style={styles.leftSection}>

        <View style={styles.iconContainer}>
          <Ionicons
            name="calendar-clear"
            size={26}
            color={LEAVE_THEME.colors.primary}
          />
        </View>

        <View style={styles.textContainer}>
          <Text style={styles.title}>
            Leaves & Holidays
          </Text>

          <Text style={styles.subtitle}>
            Manage employee leave requests and holidays
          </Text>

          <View style={styles.periodBadge}>
            <Ionicons
              name="time-outline"
              size={14}
              color={LEAVE_THEME.colors.primary}
            />

            <Text style={styles.periodText}>
              {month} {year}
            </Text>
          </View>
        </View>

      </View>

      <TouchableOpacity
        activeOpacity={0.85}
        style={styles.calendarButton}
        onPress={onCalendarPress}
      >
        <Ionicons
          name="calendar-outline"
          size={22}
          color="#FFFFFF"
        />
      </TouchableOpacity>

    </View>
  );
}

const styles = StyleSheet.create({

  container: {
    backgroundColor: "#FFFFFF",

    borderRadius: 24,

    padding: 20,

    marginBottom: 18,

    flexDirection: "row",

    justifyContent: "space-between",

    alignItems: "center",

    borderWidth: 1,

    borderColor: LEAVE_THEME.colors.border,

    ...LEAVE_THEME.shadow,
  },

  leftSection: {
    flex: 1,

    flexDirection: "row",

    alignItems: "center",
  },

  iconContainer: {
    width: 62,

    height: 62,

    borderRadius: 18,

    backgroundColor:
      LEAVE_THEME.colors.primaryLight,

    justifyContent: "center",

    alignItems: "center",
  },

  textContainer: {
    flex: 1,

    marginLeft: 16,
  },

  title: {
    fontSize: 22,

    fontWeight: "800",

    color:
      LEAVE_THEME.colors.textPrimary,
  },

  subtitle: {
    marginTop: 4,

    fontSize: 14,

    color:
      LEAVE_THEME.colors.textMuted,

    lineHeight: 20,
  },

  periodBadge: {
    alignSelf: "flex-start",

    marginTop: 10,

    flexDirection: "row",

    alignItems: "center",

    backgroundColor:
      LEAVE_THEME.colors.primaryLight,

    paddingHorizontal: 10,

    paddingVertical: 6,

    borderRadius: 20,
  },

  periodText: {
    marginLeft: 6,

    fontSize: 12,

    fontWeight: "700",

    color:
      LEAVE_THEME.colors.primary,
  },

  calendarButton: {
    width: 52,

    height: 52,

    borderRadius: 16,

    backgroundColor:
      LEAVE_THEME.colors.primary,

    justifyContent: "center",

    alignItems: "center",
  },

});