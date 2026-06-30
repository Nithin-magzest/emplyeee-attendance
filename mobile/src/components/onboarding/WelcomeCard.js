import React from "react";
import {
  View,
  Text,
  StyleSheet,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

export default function WelcomeCard({
  employeeName,
  progress,
  completedTasks,
  totalTasks,
}) {
  return (
    <View style={styles.container}>
      <View style={styles.iconContainer}>
        <Ionicons
          name="rocket"
          size={34}
          color="#FFFFFF"
        />
      </View>

      <Text style={styles.greeting}>
        Welcome,
      </Text>

      <Text style={styles.name}>
        {employeeName}
      </Text>

      <Text style={styles.subtitle}>
        Complete your onboarding journey to get
        started with the organization.
      </Text>

      <View style={styles.progressSection}>
        <View style={styles.progressHeader}>
          <Text style={styles.progressLabel}>
            Overall Progress
          </Text>

          <Text style={styles.progressValue}>
            {progress}%
          </Text>
        </View>

        <View style={styles.progressBackground}>
          <View
            style={[
              styles.progressFill,
              {
                width: `${progress}%`,
              },
            ]}
          />
        </View>

        <Text style={styles.taskText}>
          {completedTasks} of {totalTasks} tasks
          completed
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: "#173B8C",

    borderRadius: 24,

    padding: 22,

    marginBottom: 22,

    shadowColor: "#173B8C",
    shadowOpacity: 0.22,
    shadowRadius: 12,
    shadowOffset: {
      width: 0,
      height: 6,
    },

    elevation: 5,
  },

  iconContainer: {
    width: 62,
    height: 62,

    borderRadius: 18,

    backgroundColor: "rgba(255,255,255,0.18)",

    justifyContent: "center",
    alignItems: "center",

    marginBottom: 18,
  },

  greeting: {
    fontSize: 16,
    color: "#DCE8FF",
    fontWeight: "600",
  },

  name: {
    marginTop: 2,

    fontSize: 30,

    fontWeight: "800",

    color: "#FFFFFF",
  },

  subtitle: {
    marginTop: 12,

    color: "#DCE8FF",

    fontSize: 15,

    lineHeight: 24,
  },

  progressSection: {
    marginTop: 24,
  },

  progressHeader: {
    flexDirection: "row",

    justifyContent: "space-between",

    marginBottom: 10,
  },

  progressLabel: {
    color: "#FFFFFF",
    fontWeight: "700",
    fontSize: 14,
  },

  progressValue: {
    color: "#FFFFFF",
    fontWeight: "800",
    fontSize: 15,
  },

  progressBackground: {
    height: 10,

    borderRadius: 10,

    backgroundColor: "rgba(255,255,255,0.25)",

    overflow: "hidden",
  },

  progressFill: {
    height: "100%",

    borderRadius: 10,

    backgroundColor: "#22C55E",
  },

  taskText: {
    marginTop: 10,

    color: "#DCE8FF",

    fontWeight: "600",

    fontSize: 13,
  },
});