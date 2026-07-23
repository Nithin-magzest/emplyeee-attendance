import React from "react";

import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

import LEAVE_THEME from "../../constants/leaveTheme";

export default function HolidayCard({
  holiday,
  onPress,
}) {
  const day = holiday.date.split(" ")[0];
  const month = holiday.date.split(" ")[1];

  return (
    <TouchableOpacity
      activeOpacity={0.9}
      style={styles.card}
      onPress={() => onPress && onPress(holiday)}
    >
      {/* Date Card */}

      <View style={styles.dateCard}>

        <Text style={styles.day}>
          {day}
        </Text>

        <Text style={styles.month}>
          {month}
        </Text>

      </View>

      {/* Content */}

      <View style={styles.content}>

        <View style={styles.topRow}>

          <Text
            numberOfLines={1}
            style={styles.title}
          >
            {holiday.title}
          </Text>

          <View style={styles.badge}>

            <Text style={styles.badgeText}>
              {holiday.type}
            </Text>

          </View>

        </View>

        <View style={styles.infoRow}>

          <Ionicons
            name="calendar-outline"
            size={15}
            color={LEAVE_THEME.colors.textMuted}
          />

          <Text style={styles.dayText}>
            {holiday.day}
          </Text>

        </View>

        <View style={styles.footer}>

          <View style={styles.dot} />

          <Text style={styles.footerText}>
            Company Holiday
          </Text>

        </View>

      </View>

      <Ionicons
        name="chevron-forward"
        size={20}
        color={LEAVE_THEME.colors.textLight}
      />

    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({

  card: {
    backgroundColor: "#FFFFFF",

    borderRadius: 22,

    padding: 18,

    marginBottom: 16,

    flexDirection: "row",

    alignItems: "center",

    borderWidth: 1,

    borderColor:
      LEAVE_THEME.colors.border,

    ...LEAVE_THEME.shadow,
  },

  dateCard: {
    width: 70,

    height: 76,

    borderRadius: 18,

    backgroundColor:
      LEAVE_THEME.colors.primaryLight,

    justifyContent: "center",

    alignItems: "center",
  },

  day: {
    fontSize: 28,

    fontWeight: "800",

    color:
      LEAVE_THEME.colors.primary,
  },

  month: {
    marginTop: 2,

    fontSize: 13,

    fontWeight: "700",

    color:
      LEAVE_THEME.colors.primary,
  },

  content: {
    flex: 1,

    marginLeft: 16,
  },

  topRow: {
    flexDirection: "row",

    alignItems: "center",

    justifyContent: "space-between",
  },

  title: {
    flex: 1,

    fontSize: 17,

    fontWeight: "800",

    color:
      LEAVE_THEME.colors.textPrimary,

    marginRight: 8,
  },

  badge: {
    backgroundColor:
      LEAVE_THEME.colors.successLight,

    paddingHorizontal: 10,

    paddingVertical: 5,

    borderRadius: 20,
  },

  badgeText: {
    fontSize: 11,

    fontWeight: "700",

    color:
      LEAVE_THEME.colors.success,
  },

  infoRow: {
    flexDirection: "row",

    alignItems: "center",

    marginTop: 10,
  },

  dayText: {
    marginLeft: 6,

    fontSize: 13,

    color:
      LEAVE_THEME.colors.textMuted,
  },

  footer: {
    flexDirection: "row",

    alignItems: "center",

    marginTop: 12,
  },

  dot: {
    width: 8,

    height: 8,

    borderRadius: 4,

    backgroundColor:
      LEAVE_THEME.colors.primary,

    marginRight: 8,
  },

  footerText: {
    fontSize: 13,

    fontWeight: "600",

    color:
      LEAVE_THEME.colors.textSecondary,
  },

});