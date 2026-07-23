import React from "react";
import {
  View,
  Text,
  StyleSheet,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

export default function PolicyContentCard({
  policy,
}) {
  if (!policy) return null;

  return (
    <View style={styles.container}>
      {/* Highlight Card */}

      {policy.highlight ? (
        <View style={styles.highlightCard}>
          <Ionicons
            name="information-circle"
            size={22}
            color="#173B8C"
          />

          <Text style={styles.highlightText}>
            {policy.highlight}
          </Text>
        </View>
      ) : null}

      {/* Description */}

      {policy.description ? (
        <Text style={styles.description}>
          {policy.description}
        </Text>
      ) : null}

      {/* Sections */}

      {policy.sections.map((section, index) => (
        <View
          key={index}
          style={styles.section}
        >
          <Text style={styles.sectionTitle}>
            {section.title}
          </Text>

          {section.points.map((point, pointIndex) => (
            <View
              key={pointIndex}
              style={styles.pointRow}
            >
              <View style={styles.bullet} />

              <Text style={styles.point}>
                {point}
              </Text>
            </View>
          ))}
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: "#FFFFFF",

    borderRadius: 22,

    padding: 22,

    borderWidth: 1,
    borderColor: "#E6ECF5",

    shadowColor: "#000",

    shadowOpacity: 0.05,

    shadowRadius: 10,

    shadowOffset: {
      width: 0,
      height: 5,
    },

    elevation: 3,

    marginBottom: 28,
  },

  highlightCard: {
    flexDirection: "row",

    alignItems: "flex-start",

    backgroundColor: "#EEF5FF",

    borderLeftWidth: 5,

    borderLeftColor: "#173B8C",

    borderRadius: 14,

    padding: 16,

    marginBottom: 20,
  },

  highlightText: {
    flex: 1,

    marginLeft: 12,

    color: "#173B8C",

    fontSize: 15,

    lineHeight: 23,

    fontWeight: "700",
  },

  description: {
    fontSize: 15,

    color: "#475569",

    lineHeight: 25,

    marginBottom: 24,
  },

  section: {
    marginBottom: 28,
  },

  sectionTitle: {
    fontSize: 19,

    fontWeight: "800",

    color: "#0F172A",

    marginBottom: 16,
  },

  pointRow: {
    flexDirection: "row",

    alignItems: "flex-start",

    marginBottom: 14,
  },

  bullet: {
    width: 8,

    height: 8,

    borderRadius: 4,

    backgroundColor: "#2563EB",

    marginTop: 8,

    marginRight: 14,
  },

  point: {
    flex: 1,

    fontSize: 15,

    color: "#475569",

    lineHeight: 24,
  },
});