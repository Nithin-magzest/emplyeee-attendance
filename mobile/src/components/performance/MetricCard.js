import React from "react";
import {
  View,
  Text,
  StyleSheet,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

export default function MetricCard({
  icon,
  title,
  score,
  color,
  background,
}) {
  return (
    <View style={styles.container}>
      <View
        style={[
          styles.iconContainer,
          {
            backgroundColor: background,
          },
        ]}
      >
        <Ionicons
          name={icon}
          size={24}
          color={color}
        />
      </View>

      <View style={styles.content}>
        <View style={styles.header}>
          <Text style={styles.title}>
            {title}
          </Text>

          <Text
            style={[
              styles.score,
              {
                color,
              },
            ]}
          >
            {score}%
          </Text>
        </View>

        <View style={styles.progressBackground}>
          <View
            style={[
              styles.progressFill,
              {
                width: `${score}%`,
                backgroundColor: color,
              },
            ]}
          />
        </View>

        <Text style={styles.description}>
          {score >= 90
            ? "Excellent performance"
            : score >= 75
            ? "Good performance"
            : score >= 60
            ? "Average performance"
            : "Needs improvement"}
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: "#FFFFFF",

    borderRadius: 20,

    padding: 18,

    flexDirection: "row",

    alignItems: "center",

    marginBottom: 16,

    borderWidth: 1,
    borderColor: "#E8EDF3",

    shadowColor: "#000",
    shadowOpacity: 0.04,
    shadowRadius: 8,
    shadowOffset: {
      width: 0,
      height: 4,
    },

    elevation: 2,
  },

  iconContainer: {
    width: 58,
    height: 58,

    borderRadius: 16,

    justifyContent: "center",
    alignItems: "center",
  },

  content: {
    flex: 1,
    marginLeft: 16,
  },

  header: {
    flexDirection: "row",

    justifyContent: "space-between",

    alignItems: "center",

    marginBottom: 10,
  },

  title: {
    fontSize: 16,

    fontWeight: "800",

    color: "#0F172A",
  },

  score: {
    fontSize: 20,

    fontWeight: "900",
  },

  progressBackground: {
    height: 10,

    backgroundColor: "#E2E8F0",

    borderRadius: 10,

    overflow: "hidden",
  },

  progressFill: {
    height: "100%",

    borderRadius: 10,
  },

  description: {
    marginTop: 10,

    fontSize: 13,

    color: "#64748B",

    fontWeight: "600",
  },
});