import React from "react";
import {
  View,
  Text,
  StyleSheet,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

function InfoRow({
  icon,
  label,
  value,
}) {
  return (
    <View style={styles.row}>
      <View style={styles.left}>
        <View style={styles.iconContainer}>
          <Ionicons
            name={icon}
            size={18}
            color="#173B8C"
          />
        </View>

        <View style={styles.textContainer}>
          <Text style={styles.label}>
            {label}
          </Text>

          <Text style={styles.value}>
            {value}
          </Text>
        </View>
      </View>
    </View>
  );
}

export default function CompanyInfoCard({
  department,
  designation,
  manager,
  officeLocation,
  joiningDate,
  workMode,
  employmentType,
  shift,
}) {
  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Ionicons
          name="business-outline"
          size={22}
          color="#173B8C"
        />

        <Text style={styles.title}>
          Company Information
        </Text>
      </View>

      <InfoRow
        icon="briefcase-outline"
        label="Designation"
        value={designation}
      />

      <InfoRow
        icon="business-outline"
        label="Department"
        value={department}
      />

      <InfoRow
        icon="person-outline"
        label="Reporting Manager"
        value={manager}
      />

      <InfoRow
        icon="location-outline"
        label="Office Location"
        value={officeLocation}
      />

      <InfoRow
        icon="calendar-outline"
        label="Joining Date"
        value={joiningDate}
      />

      <InfoRow
        icon="laptop-outline"
        label="Work Mode"
        value={workMode}
      />

      <InfoRow
        icon="people-outline"
        label="Employment Type"
        value={employmentType}
      />

      <InfoRow
        icon="time-outline"
        label="Working Shift"
        value={shift}
      />
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

    fontSize: 18,

    fontWeight: "800",

    color: "#0F172A",
  },

  row: {
    paddingVertical: 12,

    borderBottomWidth: 1,
    borderBottomColor: "#EEF2F7",
  },

  left: {
    flexDirection: "row",
    alignItems: "center",
  },

  iconContainer: {
    width: 42,
    height: 42,

    borderRadius: 14,

    backgroundColor: "#EEF4FF",

    justifyContent: "center",
    alignItems: "center",
  },

  textContainer: {
    flex: 1,

    marginLeft: 14,
  },

  label: {
    fontSize: 13,

    fontWeight: "600",

    color: "#64748B",
  },

  value: {
    marginTop: 4,

    fontSize: 15,

    fontWeight: "700",

    color: "#0F172A",
  },
});