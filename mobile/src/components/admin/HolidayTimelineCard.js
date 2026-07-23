import React from "react";

import {
  View,
  Text,
  StyleSheet,
  ScrollView,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

import LEAVE_THEME from "../../constants/leaveTheme";

export default function HolidayTimelineCard({
  holidays = [],
}) {
  return (
    <View style={styles.container}>

      <View style={styles.header}>

        <Text style={styles.title}>
          Upcoming Holidays
        </Text>

        <Text style={styles.subtitle}>
          Company Calendar
        </Text>

      </View>

      <ScrollView
        showsVerticalScrollIndicator={false}
      >

        {holidays.map((holiday, index) => {

          const parts = holiday.date.split(" ");

          const day = parts[0];
          const month = parts[1];

          return (

            <View
              key={holiday.id}
              style={styles.item}
            >

              {/* Timeline */}

              <View style={styles.timeline}>

                <View style={styles.circle} />

                {index !==
                  holidays.length - 1 && (
                  <View
                    style={styles.line}
                  />
                )}

              </View>

              {/* Date */}

              <View style={styles.dateBox}>

                <Text style={styles.day}>
                  {day}
                </Text>

                <Text style={styles.month}>
                  {month}
                </Text>

              </View>

              {/* Content */}

              <View style={styles.content}>

                <Text
                  style={styles.name}
                >
                  {holiday.title}
                </Text>

                <View
                  style={styles.row}
                >

                  <Ionicons
                    name="calendar-outline"
                    size={14}
                    color={
                      LEAVE_THEME.colors
                        .textMuted
                    }
                  />

                  <Text
                    style={styles.dayName}
                  >
                    {holiday.day}
                  </Text>

                </View>

                <View
                  style={styles.badge}
                >

                  <Text
                    style={
                      styles.badgeText
                    }
                  >
                    {holiday.type}
                  </Text>

                </View>

              </View>

            </View>

          );

        })}

      </ScrollView>

    </View>
  );
}

const styles = StyleSheet.create({

  container: {
    backgroundColor: "#FFFFFF",

    borderRadius: 22,

    padding: 20,

    marginBottom: 20,

    borderWidth: 1,

    borderColor:
      LEAVE_THEME.colors.border,

    ...LEAVE_THEME.shadow,
  },

  header: {
    marginBottom: 22,
  },

  title: {
    fontSize: 18,

    fontWeight: "800",

    color:
      LEAVE_THEME.colors.textPrimary,
  },

  subtitle: {
    marginTop: 4,

    fontSize: 13,

    color:
      LEAVE_THEME.colors.textMuted,
  },

  item: {
    flexDirection: "row",

    marginBottom: 24,
  },

  timeline: {
    width: 24,

    alignItems: "center",
  },

  circle: {
    width: 12,

    height: 12,

    borderRadius: 6,

    backgroundColor:
      LEAVE_THEME.colors.primary,
  },

  line: {
    flex: 1,

    width: 2,

    backgroundColor:
      LEAVE_THEME.colors.divider,

    marginTop: 4,
  },

  dateBox: {
    width: 62,

    height: 62,

    borderRadius: 16,

    backgroundColor:
      LEAVE_THEME.colors.primaryLight,

    justifyContent: "center",

    alignItems: "center",

    marginHorizontal: 14,
  },

  day: {
    fontSize: 22,

    fontWeight: "800",

    color:
      LEAVE_THEME.colors.primary,
  },

  month: {
    marginTop: 2,

    fontSize: 12,

    fontWeight: "700",

    color:
      LEAVE_THEME.colors.primary,
  },

  content: {
    flex: 1,

    paddingTop: 2,
  },

  name: {
    fontSize: 16,

    fontWeight: "800",

    color:
      LEAVE_THEME.colors.textPrimary,
  },

  row: {
    flexDirection: "row",

    alignItems: "center",

    marginTop: 8,
  },

  dayName: {
    marginLeft: 6,

    fontSize: 13,

    color:
      LEAVE_THEME.colors.textMuted,
  },

  badge: {
    alignSelf: "flex-start",

    marginTop: 10,

    backgroundColor:
      LEAVE_THEME.colors.successLight,

    paddingHorizontal: 10,

    paddingVertical: 5,

    borderRadius: 18,
  },

  badgeText: {
    fontSize: 11,

    fontWeight: "700",

    color:
      LEAVE_THEME.colors.success,
  },

});