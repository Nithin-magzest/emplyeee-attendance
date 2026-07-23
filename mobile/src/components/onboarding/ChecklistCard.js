import React from "react";
import {
  View,
  Text,
  StyleSheet,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

export default function ChecklistCard({
  items = [],
}) {
  const completedCount = items.filter(
    (item) => item.completed
  ).length;

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View style={styles.titleRow}>
          <Ionicons
            name="checkmark-done-outline"
            size={22}
            color="#173B8C"
          />

          <Text style={styles.title}>
            Onboarding Checklist
          </Text>
        </View>

        <View style={styles.countBadge}>
          <Text style={styles.countText}>
            {completedCount}/{items.length}
          </Text>
        </View>
      </View>

      {items.map((item, index) => (
        <View
          key={`${item.title}-${index}`}
          style={[
            styles.row,
            index === items.length - 1 && {
              borderBottomWidth: 0,
            },
          ]}
        >
          <View
            style={[
              styles.iconContainer,
              {
                backgroundColor: item.completed
                  ? "#ECFDF5"
                  : "#FFF7ED",
              },
            ]}
          >
            <Ionicons
              name={
                item.completed
                  ? "checkmark-circle"
                  : "ellipse-outline"
              }
              size={22}
              color={
                item.completed
                  ? "#22C55E"
                  : "#F59E0B"
              }
            />
          </View>

          <View style={styles.content}>
            <Text
              style={[
                styles.taskTitle,
                item.completed && {
                  textDecorationLine:
                    "line-through",
                  color: "#94A3B8",
                },
              ]}
            >
              {item.title}
            </Text>

            <Text style={styles.subtitle}>
              {item.subtitle}
            </Text>
          </View>

          <Text
            style={[
              styles.status,
              {
                color: item.completed
                  ? "#16A34A"
                  : "#D97706",
              },
            ]}
          >
            {item.completed
              ? "Done"
              : "Pending"}
          </Text>
        </View>
      ))}
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

    justifyContent: "space-between",

    alignItems: "center",

    marginBottom: 18,
  },

  titleRow: {
    flexDirection: "row",
    alignItems: "center",
  },

  title: {
    marginLeft: 10,

    fontSize: 18,

    fontWeight: "800",

    color: "#0F172A",
  },

  countBadge: {
    backgroundColor: "#EEF4FF",

    paddingHorizontal: 12,
    paddingVertical: 6,

    borderRadius: 20,
  },

  countText: {
    color: "#173B8C",

    fontWeight: "800",

    fontSize: 13,
  },

  row: {
    flexDirection: "row",

    alignItems: "center",

    paddingVertical: 14,

    borderBottomWidth: 1,

    borderBottomColor: "#EEF2F7",
  },

  iconContainer: {
    width: 44,
    height: 44,

    borderRadius: 14,

    justifyContent: "center",
    alignItems: "center",
  },

  content: {
    flex: 1,

    marginLeft: 14,
  },

  taskTitle: {
    fontSize: 15,

    fontWeight: "700",

    color: "#0F172A",
  },

  subtitle: {
    marginTop: 4,

    fontSize: 13,

    color: "#64748B",

    lineHeight: 18,
  },

  status: {
    fontSize: 12,

    fontWeight: "800",
  },
});