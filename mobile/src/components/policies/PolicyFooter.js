import React from "react";
import {
  View,
  Text,
  StyleSheet,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

function FooterRow({
  icon,
  label,
  value,
  color,
}) {
  return (
    <View style={styles.row}>
      <View style={styles.left}>
        <Ionicons
          name={icon}
          size={20}
          color={color}
        />

        <Text style={styles.label}>
          {label}
        </Text>
      </View>

      <Text style={styles.value}>
        {value}
      </Text>
    </View>
  );
}

export default function PolicyFooter({
  version = "v1.2",
  updated = "01 Jul 2026",
  owner = "Human Resources",
  status = "Active",
}) {
  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Ionicons
          name="document-lock-outline"
          size={22}
          color="#173B8C"
        />

        <Text style={styles.title}>
          Document Information
        </Text>
      </View>

      <FooterRow
        icon="layers-outline"
        label="Version"
        value={version}
        color="#2563EB"
      />

      <FooterRow
        icon="calendar-outline"
        label="Last Updated"
        value={updated}
        color="#22C55E"
      />

      <FooterRow
        icon="people-outline"
        label="Owner"
        value={owner}
        color="#F59E0B"
      />

      <FooterRow
        icon="shield-checkmark-outline"
        label="Status"
        value={status}
        color="#16A34A"
      />

      <View style={styles.note}>
        <Ionicons
          name="information-circle-outline"
          size={18}
          color="#64748B"
        />

        <Text style={styles.noteText}>
          These policies are reviewed periodically.
          Employees are responsible for staying updated
          with the latest revisions.
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: "#FFFFFF",

    borderRadius: 22,

    padding: 20,

    marginBottom: 24,

    borderWidth: 1,
    borderColor: "#E8EDF3",

    shadowColor: "#0F172A",
    shadowOpacity: 0.05,
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

    marginBottom: 18,
  },

  title: {
    marginLeft: 10,

    fontSize: 19,

    fontWeight: "800",

    color: "#0F172A",
  },

  row: {
    flexDirection: "row",

    justifyContent: "space-between",

    alignItems: "center",

    paddingVertical: 14,

    borderBottomWidth: 1,

    borderBottomColor: "#EEF2F7",
  },

  left: {
    flexDirection: "row",
    alignItems: "center",
  },

  label: {
    marginLeft: 10,

    fontSize: 15,

    fontWeight: "600",

    color: "#475569",
  },

  value: {
    fontSize: 15,

    fontWeight: "700",

    color: "#173B8C",
  },

  note: {
    marginTop: 20,

    flexDirection: "row",

    alignItems: "flex-start",

    backgroundColor: "#F8FAFC",

    padding: 14,

    borderRadius: 14,
  },

  noteText: {
    flex: 1,

    marginLeft: 10,

    fontSize: 13,

    lineHeight: 20,

    color: "#64748B",
  },
});