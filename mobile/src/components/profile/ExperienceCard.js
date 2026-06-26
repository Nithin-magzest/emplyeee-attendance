import React from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";

export default function ExperienceCard({
  company = "GradZest Technologies",
  designation = "Software Engineer",
  employmentType = "Full Time",
  duration = "Jun 2025 - Present",
  location = "Hyderabad, India",
  status = "Current",
  onEdit = () => {},
  onDelete = () => {},
}) {
  return (
    <View style={styles.card}>
      {/* Header */}

      <View style={styles.header}>
        <View style={styles.iconContainer}>
          <Ionicons
            name="briefcase-outline"
            size={22}
            color="#173B8C"
          />
        </View>

        <View style={styles.headerInfo}>
          <Text style={styles.company}>
            {company}
          </Text>

          <Text style={styles.designation}>
            {designation}
          </Text>
        </View>

        <View
          style={[
            styles.badge,
            status === "Current"
              ? styles.currentBadge
              : styles.previousBadge,
          ]}
        >
          <Text
            style={[
              styles.badgeText,
              status === "Current"
                ? styles.currentText
                : styles.previousText,
            ]}
          >
            {status}
          </Text>
        </View>
      </View>

      {/* Divider */}

      <View style={styles.divider} />

      {/* Details */}

      <View style={styles.detailRow}>
        <Ionicons
          name="calendar-outline"
          size={16}
          color="#64748B"
        />

        <Text style={styles.detailText}>
          {duration}
        </Text>
      </View>

      <View style={styles.detailRow}>
        <Ionicons
          name="layers-outline"
          size={16}
          color="#64748B"
        />

        <Text style={styles.detailText}>
          {employmentType}
        </Text>
      </View>

      <View style={styles.detailRow}>
        <Ionicons
          name="location-outline"
          size={16}
          color="#64748B"
        />

        <Text style={styles.detailText}>
          {location}
        </Text>
      </View>

      {/* Footer */}

      <View style={styles.footer}>
        <TouchableOpacity
          style={styles.actionButton}
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
          style={styles.actionButton}
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

  headerInfo: {
    flex: 1,
    marginLeft: 14,
  },

  company: {
    fontSize: 16,
    fontWeight: "700",
    color: "#0F172A",
  },

  designation: {
    marginTop: 3,
    fontSize: 13,
    color: "#64748B",
    fontWeight: "600",
  },

  badge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
  },

  currentBadge: {
    backgroundColor: "#ECFDF5",
  },

  previousBadge: {
    backgroundColor: "#F8FAFC",
  },

  currentText: {
    color: "#16A34A",
  },

  previousText: {
    color: "#64748B",
  },

  badgeText: {
    fontSize: 12,
    fontWeight: "700",
  },

  divider: {
    height: 1,
    backgroundColor: "#EEF2F7",
    marginVertical: 18,
  },

  detailRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 12,
  },

  detailText: {
    marginLeft: 10,
    fontSize: 14,
    color: "#334155",
    fontWeight: "500",
  },

  footer: {
    marginTop: 10,
    flexDirection: "row",
    justifyContent: "flex-end",
  },

  actionButton: {
    flexDirection: "row",
    alignItems: "center",

    backgroundColor: "#F8FAFC",

    borderWidth: 1,
    borderColor: "#E2E8F0",

    borderRadius: 12,

    paddingHorizontal: 14,
    paddingVertical: 10,

    marginLeft: 10,
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