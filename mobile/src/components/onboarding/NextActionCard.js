import React from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

export default function NextActionCard({
  title,
  description,
  dueDate,
  priority = "High",
  onPress = () => {},
}) {
  const priorityColor =
    priority === "High"
      ? "#EF4444"
      : priority === "Medium"
      ? "#F59E0B"
      : "#22C55E";

  const priorityBg =
    priority === "High"
      ? "#FEF2F2"
      : priority === "Medium"
      ? "#FFF7ED"
      : "#ECFDF5";

  return (
    <View style={styles.container}>
      {/* Header */}

      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <Ionicons
            name="flag-outline"
            size={22}
            color="#173B8C"
          />

          <Text style={styles.title}>
            Next Action
          </Text>
        </View>

        <View
          style={[
            styles.priorityBadge,
            {
              backgroundColor: priorityBg,
            },
          ]}
        >
          <Text
            style={[
              styles.priorityText,
              {
                color: priorityColor,
              },
            ]}
          >
            {priority}
          </Text>
        </View>
      </View>

      {/* Action Card */}

      <View style={styles.actionBox}>
        <View style={styles.iconContainer}>
          <Ionicons
            name="clipboard-outline"
            size={28}
            color="#173B8C"
          />
        </View>

        <View style={styles.content}>
          <Text style={styles.actionTitle}>
            {title}
          </Text>

          <Text style={styles.description}>
            {description}
          </Text>

          <View style={styles.dateRow}>
            <Ionicons
              name="calendar-outline"
              size={16}
              color="#64748B"
            />

            <Text style={styles.date}>
              Due: {dueDate}
            </Text>
          </View>
        </View>
      </View>

      {/* Button */}

      <TouchableOpacity
        activeOpacity={0.9}
        style={styles.button}
        onPress={onPress}
      >
        <Ionicons
          name="arrow-forward"
          size={18}
          color="#FFFFFF"
        />

        <Text style={styles.buttonText}>
          Continue Onboarding
        </Text>
      </TouchableOpacity>
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

    justifyContent: "space-between",

    alignItems: "center",

    marginBottom: 18,
  },

  headerLeft: {
    flexDirection: "row",

    alignItems: "center",
  },

  title: {
    marginLeft: 10,

    fontSize: 19,

    fontWeight: "800",

    color: "#0F172A",
  },

  priorityBadge: {
    paddingHorizontal: 12,

    paddingVertical: 6,

    borderRadius: 20,
  },

  priorityText: {
    fontSize: 12,

    fontWeight: "800",
  },

  actionBox: {
    flexDirection: "row",

    alignItems: "flex-start",

    backgroundColor: "#F8FAFC",

    borderRadius: 18,

    padding: 16,

    marginBottom: 18,
  },

  iconContainer: {
    width: 56,

    height: 56,

    borderRadius: 16,

    backgroundColor: "#EEF4FF",

    justifyContent: "center",

    alignItems: "center",
  },

  content: {
    flex: 1,

    marginLeft: 16,
  },

  actionTitle: {
    fontSize: 17,

    fontWeight: "800",

    color: "#0F172A",
  },

  description: {
    marginTop: 6,

    fontSize: 14,

    lineHeight: 22,

    color: "#64748B",
  },

  dateRow: {
    flexDirection: "row",

    alignItems: "center",

    marginTop: 12,
  },

  date: {
    marginLeft: 6,

    fontSize: 13,

    fontWeight: "600",

    color: "#64748B",
  },

  button: {
    height: 54,

    borderRadius: 16,

    backgroundColor: "#173B8C",

    flexDirection: "row",

    justifyContent: "center",

    alignItems: "center",

    shadowColor: "#173B8C",
    shadowOpacity: 0.25,
    shadowRadius: 10,
    shadowOffset: {
      width: 0,
      height: 5,
    },

    elevation: 4,
  },

  buttonText: {
    marginLeft: 10,

    color: "#FFFFFF",

    fontSize: 16,

    fontWeight: "700",
  },
});