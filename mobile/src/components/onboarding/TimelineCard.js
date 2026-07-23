import React from "react";
import {
  View,
  Text,
  StyleSheet,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

export default function TimelineCard({
  timeline = [],
}) {
  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Ionicons
          name="git-branch-outline"
          size={22}
          color="#173B8C"
        />

        <Text style={styles.title}>
          Onboarding Timeline
        </Text>
      </View>

      {timeline.map((item, index) => {
        const completed =
          item.status === "Completed";

        return (
          <View
            key={`${item.title}-${index}`}
            style={styles.row}
          >
            {/* Left Timeline */}

            <View style={styles.timelineColumn}>
              <View
                style={[
                  styles.circle,
                  {
                    backgroundColor: completed
                      ? "#22C55E"
                      : "#F59E0B",
                  },
                ]}
              >
                <Ionicons
                  name={
                    completed
                      ? "checkmark"
                      : "time"
                  }
                  size={12}
                  color="#FFFFFF"
                />
              </View>

              {index !==
                timeline.length - 1 && (
                <View
                  style={styles.line}
                />
              )}
            </View>

            {/* Content */}

            <View style={styles.content}>
              <Text style={styles.stepTitle}>
                {item.title}
              </Text>

              <Text style={styles.date}>
                {item.date}
              </Text>

              <Text
                style={[
                  styles.status,
                  {
                    color: completed
                      ? "#16A34A"
                      : "#D97706",
                  },
                ]}
              >
                {item.status}
              </Text>
            </View>
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: "#FFFFFF",

    borderRadius: 22,

    padding: 20,

    marginBottom: 22,

    borderWidth: 1,

    borderColor: "#E8EDF3",

    shadowColor: "#000",

    shadowOpacity: 0.04,

    shadowRadius: 10,

    shadowOffset: {
      width: 0,
      height: 5,
    },

    elevation: 2,
  },

  header: {
    flexDirection: "row",

    alignItems: "center",

    marginBottom: 22,
  },

  title: {
    marginLeft: 10,

    fontSize: 18,

    fontWeight: "800",

    color: "#0F172A",
  },

  row: {
    flexDirection: "row",

    marginBottom: 6,
  },

  timelineColumn: {
    width: 34,

    alignItems: "center",
  },

  circle: {
    width: 24,

    height: 24,

    borderRadius: 12,

    justifyContent: "center",

    alignItems: "center",
  },

  line: {
    width: 2,

    flex: 1,

    backgroundColor: "#CBD5E1",

    marginTop: 4,

    marginBottom: -4,
  },

  content: {
    flex: 1,

    paddingBottom: 22,

    paddingLeft: 12,
  },

  stepTitle: {
    fontSize: 16,

    fontWeight: "800",

    color: "#0F172A",
  },

  date: {
    marginTop: 5,

    fontSize: 13,

    color: "#64748B",

    fontWeight: "600",
  },

  status: {
    marginTop: 8,

    fontSize: 13,

    fontWeight: "700",
  },
});