import React from "react";
import {
  View,
  Text,
  StyleSheet,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";

export default function CompOffEmptyState({
  title = "No Records Found",
  subtitle = "Your overtime and comp-off records will appear here once they become available.",
}) {
  return (
    <View style={styles.container}>
      <View style={styles.iconContainer}>
        <Ionicons
          name="document-text-outline"
          size={52}
          color="#173B8C"
        />
      </View>

      <Text style={styles.title}>
        {title}
      </Text>

      <Text style={styles.subtitle}>
        {subtitle}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: "#FFFFFF",

    borderRadius: 24,

    paddingVertical: 50,
    paddingHorizontal: 28,

    marginTop: 20,
    marginBottom: 30,

    alignItems: "center",
    justifyContent: "center",

    borderWidth: 1,
    borderColor: "#E8EDF5",

    shadowColor: "#0F172A",
    shadowOpacity: 0.05,
    shadowRadius: 16,
    shadowOffset: {
      width: 0,
      height: 8,
    },

    elevation: 4,
  },

  iconContainer: {
    width: 90,
    height: 90,

    borderRadius: 45,

    backgroundColor: "#EEF4FF",

    justifyContent: "center",
    alignItems: "center",

    marginBottom: 22,
  },

  title: {
    fontSize: 22,
    fontWeight: "800",
    color: "#0F172A",
    textAlign: "center",
  },

  subtitle: {
    marginTop: 12,

    fontSize: 14,
    lineHeight: 24,

    color: "#64748B",

    textAlign: "center",

    maxWidth: 280,
  },
});