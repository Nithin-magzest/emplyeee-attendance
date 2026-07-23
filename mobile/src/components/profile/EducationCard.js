import React from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";

export default function EducationCard({
  degree = "Bachelor of Technology",
  specialization = "Computer Science & Engineering",
  institute = "IIIT Basar",
  duration = "2021 - 2025",
  score = "8.62 CGPA",
  status = "Completed",
  onEdit = () => {},
  onDelete = () => {},
}) {
  return (
    <View style={styles.card}>
      {/* Top */}

      <View style={styles.header}>
        <View style={styles.iconContainer}>
          <Ionicons
            name="school-outline"
            size={22}
            color="#173B8C"
          />
        </View>

        <View style={styles.info}>
          <Text style={styles.degree}>
            {degree}
          </Text>

          <Text style={styles.specialization}>
            {specialization}
          </Text>
        </View>

        <View style={styles.statusBadge}>
          <Text style={styles.status}>
            {status}
          </Text>
        </View>
      </View>

      {/* Body */}

      <View style={styles.details}>
        <View style={styles.row}>
          <Ionicons
            name="business-outline"
            size={16}
            color="#64748B"
          />

          <Text style={styles.text}>
            {institute}
          </Text>
        </View>

        <View style={styles.row}>
          <Ionicons
            name="calendar-outline"
            size={16}
            color="#64748B"
          />

          <Text style={styles.text}>
            {duration}
          </Text>
        </View>

        <View style={styles.row}>
          <Ionicons
            name="ribbon-outline"
            size={16}
            color="#64748B"
          />

          <Text style={styles.text}>
            {score}
          </Text>
        </View>
      </View>

      {/* Footer */}

      <View style={styles.footer}>
        <TouchableOpacity
          style={styles.button}
          onPress={onEdit}
        >
          <Ionicons
            name="create-outline"
            size={18}
            color="#173B8C"
          />

          <Text style={styles.editText}>
            Edit
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.button}
          onPress={onDelete}
        >
          <Ionicons
            name="trash-outline"
            size={18}
            color="#EF4444"
          />

          <Text style={styles.deleteText}>
            Delete
          </Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#FFFFFF",

    borderRadius: 22,

    padding: 18,

    marginBottom: 16,

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
    alignItems: "center",
  },

  iconContainer: {
    width: 54,
    height: 54,

    borderRadius: 16,

    backgroundColor: "#EEF4FF",

    justifyContent: "center",
    alignItems: "center",
  },

  info: {
    flex: 1,
    marginLeft: 14,
  },

  degree: {
    fontSize: 16,
    fontWeight: "700",
    color: "#0F172A",
  },

  specialization: {
    marginTop: 3,
    fontSize: 13,
    color: "#64748B",
  },

  statusBadge: {
    backgroundColor: "#ECFDF5",

    paddingHorizontal: 12,
    paddingVertical: 6,

    borderRadius: 20,
  },

  status: {
    color: "#16A34A",

    fontSize: 12,

    fontWeight: "700",
  },

  details: {
    marginTop: 18,
  },

  row: {
    flexDirection: "row",
    alignItems: "center",

    marginBottom: 12,
  },

  text: {
    marginLeft: 10,

    color: "#334155",

    fontSize: 14,

    fontWeight: "500",
  },

  footer: {
    marginTop: 12,

    flexDirection: "row",

    justifyContent: "flex-end",
  },

  button: {
    flexDirection: "row",

    alignItems: "center",

    backgroundColor: "#F8FAFC",

    paddingHorizontal: 14,
    paddingVertical: 10,

    borderRadius: 12,

    marginLeft: 10,

    borderWidth: 1,

    borderColor: "#E2E8F0",
  },

  editText: {
    marginLeft: 6,

    color: "#173B8C",

    fontWeight: "700",
  },

  deleteText: {
    marginLeft: 6,

    color: "#EF4444",

    fontWeight: "700",
  },
});