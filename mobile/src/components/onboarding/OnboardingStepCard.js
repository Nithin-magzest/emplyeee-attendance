import React from "react";
import {
  View,
  Text,
  StyleSheet,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

export default function OnboardingStepCard({
  title,
  subtitle,
  completed = false,
}) {
  return (
    <View style={styles.container}>
      <View
        style={[
          styles.iconContainer,
          {
            backgroundColor: completed
              ? "#ECFDF5"
              : "#FFF7ED",
          },
        ]}
      >
        <Ionicons
          name={
            completed
              ? "checkmark-circle"
              : "time"
          }
          size={26}
          color={
            completed
              ? "#22C55E"
              : "#F59E0B"
          }
        />
      </View>

      <View style={styles.content}>
        <Text style={styles.title}>
          {title}
        </Text>

        <Text style={styles.subtitle}>
          {subtitle}
        </Text>
      </View>

      <View
        style={[
          styles.badge,
          {
            backgroundColor: completed
              ? "#ECFDF5"
              : "#FFF7ED",
          },
        ]}
      >
        <Text
          style={[
            styles.badgeText,
            {
              color: completed
                ? "#16A34A"
                : "#D97706",
            },
          ]}
        >
          {completed
            ? "Completed"
            : "Pending"}
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",

    alignItems: "center",

    backgroundColor: "#FFFFFF",

    borderRadius: 20,

    padding: 16,

    marginBottom: 14,

    borderWidth: 1,
    borderColor: "#E8EDF3",

    shadowColor: "#000",
    shadowOpacity: 0.03,
    shadowRadius: 8,
    shadowOffset: {
      width: 0,
      height: 4,
    },

    elevation: 2,
  },

  iconContainer: {
    width: 56,
    height: 56,

    borderRadius: 18,

    justifyContent: "center",
    alignItems: "center",
  },

  content: {
    flex: 1,

    marginLeft: 16,
  },

  title: {
    fontSize: 16,

    fontWeight: "800",

    color: "#0F172A",
  },

  subtitle: {
    marginTop: 5,

    fontSize: 13,

    lineHeight: 20,

    color: "#64748B",
  },

  badge: {
    paddingHorizontal: 14,
    paddingVertical: 7,

    borderRadius: 30,
  },

  badgeText: {
    fontSize: 12,

    fontWeight: "800",
  },
});