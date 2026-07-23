import React from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

function ContactRow({
  icon,
  title,
  subtitle,
  color,
  background,
}) {
  return (
    <TouchableOpacity
      activeOpacity={0.85}
      style={styles.row}
    >
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
          size={22}
          color={color}
        />
      </View>

      <View style={styles.info}>
        <Text style={styles.title}>
          {title}
        </Text>

        <Text style={styles.subtitle}>
          {subtitle}
        </Text>
      </View>

      <Ionicons
        name="chevron-forward"
        size={20}
        color="#CBD5E1"
      />
    </TouchableOpacity>
  );
}

export default function ContactInfoCard() {
  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Ionicons
          name="call-outline"
          size={22}
          color="#173B8C"
        />

        <Text style={styles.headerTitle}>
          Need Assistance?
        </Text>
      </View>

      <Text style={styles.description}>
        Contact the appropriate department if you
        have questions regarding company policies or
        employee guidelines.
      </Text>

      <ContactRow
        icon="people-outline"
        title="Human Resources"
        subtitle="hr@company.com"
        color="#173B8C"
        background="#EEF4FF"
      />

      <ContactRow
        icon="desktop-outline"
        title="IT Support"
        subtitle="support@company.com"
        color="#2563EB"
        background="#EEF4FF"
      />

      <ContactRow
        icon="wallet-outline"
        title="Payroll"
        subtitle="payroll@company.com"
        color="#16A34A"
        background="#ECFDF5"
      />

      <ContactRow
        icon="shield-checkmark-outline"
        title="Compliance Team"
        subtitle="compliance@company.com"
        color="#EA580C"
        background="#FFF7ED"
      />
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

    marginBottom: 10,
  },

  headerTitle: {
    marginLeft: 10,

    fontSize: 19,

    fontWeight: "800",

    color: "#0F172A",
  },

  description: {
    fontSize: 14,

    color: "#64748B",

    lineHeight: 22,

    marginBottom: 20,
  },

  row: {
    flexDirection: "row",

    alignItems: "center",

    paddingVertical: 14,

    borderBottomWidth: 1,

    borderBottomColor: "#EEF2F7",
  },

  iconContainer: {
    width: 50,
    height: 50,

    borderRadius: 16,

    justifyContent: "center",

    alignItems: "center",
  },

  info: {
    flex: 1,

    marginLeft: 14,
  },

  title: {
    fontSize: 15,

    fontWeight: "700",

    color: "#0F172A",
  },

  subtitle: {
    marginTop: 4,

    fontSize: 13,

    color: "#64748B",
  },
});