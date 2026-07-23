import React from "react";
import {
  View,
  Text,
  StyleSheet,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";

export default function ProfileCompletionCard({
  percentage = 82,
  completed = 18,
  total = 22,
}) {
  return (
    <View style={styles.card}>
      {/* Header */}

      <View style={styles.header}>
        <View>
          <Text style={styles.title}>
            Profile Completion
          </Text>

          <Text style={styles.subtitle}>
            Complete your profile for a better experience
          </Text>
        </View>

        <View style={styles.percentBox}>
          <Text style={styles.percent}>
            {percentage}%
          </Text>
        </View>
      </View>

      {/* Progress */}

      <View style={styles.progressTrack}>
        <View
          style={[
            styles.progressFill,
            {
              width: `${percentage}%`,
            },
          ]}
        />
      </View>

      {/* Footer */}

      <View style={styles.footer}>
        <View style={styles.footerLeft}>
          <View style={styles.checkIcon}>
            <Ionicons
              name="checkmark-circle"
              size={18}
              color="#16A34A"
            />
          </View>

          <View>
            <Text style={styles.completed}>
              {completed} of {total} sections completed
            </Text>

            <Text style={styles.remaining}>
              {total - completed} sections remaining
            </Text>
          </View>
        </View>

        <Ionicons
          name="chevron-forward"
          size={18}
          color="#94A3B8"
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#FFFFFF",

    borderRadius: 22,

    padding: 20,

    marginBottom: 20,

    borderWidth: 1,
    borderColor: "#E8EDF3",

    shadowColor: "#0F172A",
    shadowOpacity: 0.05,
    shadowRadius: 12,
    shadowOffset: {
      width: 0,
      height: 6,
    },

    elevation: 3,
  },

  header: {
    flexDirection: "row",

    justifyContent: "space-between",

    alignItems: "center",
  },

  title: {
    fontSize: 18,

    fontWeight: "700",

    color: "#0F172A",
  },

  subtitle: {
    marginTop: 4,

    fontSize: 13,

    color: "#64748B",

    lineHeight: 18,
  },

  percentBox: {
    width: 64,
    height: 64,

    borderRadius: 18,

    backgroundColor: "#EEF4FF",

    justifyContent: "center",

    alignItems: "center",
  },

  percent: {
    fontSize: 20,

    fontWeight: "800",

    color: "#173B8C",
  },

  progressTrack: {
    marginTop: 22,

    height: 8,

    borderRadius: 20,

    backgroundColor: "#E2E8F0",

    overflow: "hidden",
  },

  progressFill: {
    height: "100%",

    backgroundColor: "#173B8C",

    borderRadius: 20,
  },

  footer: {
    marginTop: 22,

    flexDirection: "row",

    justifyContent: "space-between",

    alignItems: "center",
  },

  footerLeft: {
    flexDirection: "row",

    alignItems: "center",

    flex: 1,
  },

  checkIcon: {
    width: 42,
    height: 42,

    borderRadius: 14,

    backgroundColor: "#ECFDF5",

    justifyContent: "center",

    alignItems: "center",

    marginRight: 12,
  },

  completed: {
    fontSize: 14,

    fontWeight: "700",

    color: "#0F172A",
  },

  remaining: {
    marginTop: 3,

    fontSize: 12,

    color: "#64748B",
  },
});