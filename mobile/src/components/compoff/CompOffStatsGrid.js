import React from "react";
import {
  View,
  Text,
  StyleSheet,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";

const DATA = [
  {
    key: "otHours",
    title: "OT Hours",
    icon: "time-outline",
    color: "#2563EB",
    bg: "#EEF4FF",
    suffix: "hrs",
  },
  {
    key: "availableDays",
    title: "Available",
    icon: "calendar-clear-outline",
    color: "#16A34A",
    bg: "#ECFDF5",
    suffix: "Days",
  },
  {
    key: "usedDays",
    title: "Used",
    icon: "remove-circle-outline",
    color: "#EA580C",
    bg: "#FFF7ED",
    suffix: "Days",
  },
  {
    key: "earnedDays",
    title: "Earned",
    icon: "ribbon-outline",
    color: "#7C3AED",
    bg: "#F5F3FF",
    suffix: "Days",
  },
];

export default function CompOffStatsGrid({
  otHours = "0.0",
  availableDays = "0.0",
  usedDays = "0.0",
  earnedDays = "0.0",
}) {
  const values = {
    otHours,
    availableDays,
    usedDays,
    earnedDays,
  };

  return (
    <View style={styles.container}>
      {DATA.map((item) => (
        <View
          key={item.key}
          style={styles.card}
        >
          <View
            style={[
              styles.iconContainer,
              {
                backgroundColor: item.bg,
              },
            ]}
          >
            <Ionicons
              name={item.icon}
              size={22}
              color={item.color}
            />
          </View>

          <Text style={styles.value}>
            {values[item.key]}
          </Text>

          <Text style={styles.suffix}>
            {item.suffix}
          </Text>

          <Text style={styles.title}>
            {item.title}
          </Text>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "space-between",
    marginBottom: 24,
  },

  card: {
    width: "48%",

    backgroundColor: "#FFFFFF",

    borderRadius: 22,

    paddingVertical: 22,
    paddingHorizontal: 18,

    marginBottom: 16,

    borderWidth: 1,
    borderColor: "#EEF2F7",

    shadowColor: "#0F172A",
    shadowOpacity: 0.05,
    shadowRadius: 14,
    shadowOffset: {
      width: 0,
      height: 6,
    },

    elevation: 4,
  },

  iconContainer: {
    width: 52,
    height: 52,

    borderRadius: 16,

    justifyContent: "center",
    alignItems: "center",
  },

  value: {
    marginTop: 18,

    fontSize: 30,

    fontWeight: "800",

    color: "#0F172A",

    letterSpacing: -0.8,
  },

  suffix: {
    marginTop: 2,

    fontSize: 12,

    color: "#64748B",

    fontWeight: "600",
  },

  title: {
    marginTop: 18,

    fontSize: 14,

    fontWeight: "700",

    color: "#334155",
  },
});