import React from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

export default function UpcomingReviewCard({
  reviewDate,
  reviewType,
  reviewer,
  status,
  onPress = () => {},
}) {
  const statusColor =
    status === "Scheduled"
      ? "#2563EB"
      : status === "Completed"
      ? "#16A34A"
      : "#F59E0B";

  const statusBackground =
    status === "Scheduled"
      ? "#EEF4FF"
      : status === "Completed"
      ? "#ECFDF5"
      : "#FFF7ED";

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View style={styles.iconContainer}>
          <Ionicons
            name="calendar-outline"
            size={24}
            color="#173B8C"
          />
        </View>

        <View style={styles.headerContent}>
          <Text style={styles.title}>
            Upcoming Review
          </Text>

          <Text style={styles.subtitle}>
            Your next performance evaluation
          </Text>
        </View>
      </View>

      <View style={styles.divider} />

      <View style={styles.row}>
        <Ionicons
          name="calendar-number-outline"
          size={20}
          color="#173B8C"
        />

        <View style={styles.info}>
          <Text style={styles.label}>
            Review Date
          </Text>

          <Text style={styles.value}>
            {reviewDate}
          </Text>
        </View>
      </View>

      <View style={styles.row}>
        <Ionicons
          name="document-text-outline"
          size={20}
          color="#173B8C"
        />

        <View style={styles.info}>
          <Text style={styles.label}>
            Review Type
          </Text>

          <Text style={styles.value}>
            {reviewType}
          </Text>
        </View>
      </View>

      <View style={styles.row}>
        <Ionicons
          name="person-outline"
          size={20}
          color="#173B8C"
        />

        <View style={styles.info}>
          <Text style={styles.label}>
            Reviewer
          </Text>

          <Text style={styles.value}>
            {reviewer}
          </Text>
        </View>
      </View>

      <View style={styles.bottom}>
        <View
          style={[
            styles.statusBadge,
            {
              backgroundColor:
                statusBackground,
            },
          ]}
        >
          <Text
            style={[
              styles.statusText,
              {
                color: statusColor,
              },
            ]}
          >
            {status}
          </Text>
        </View>

        <TouchableOpacity
          activeOpacity={0.85}
          style={styles.button}
          onPress={onPress}
        >
          <Ionicons
            name="eye-outline"
            size={18}
            color="#FFFFFF"
          />

          <Text style={styles.buttonText}>
            View Details
          </Text>
        </TouchableOpacity>
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
  },

  iconContainer: {
    width: 58,
    height: 58,

    borderRadius: 16,

    backgroundColor: "#EEF4FF",

    justifyContent: "center",
    alignItems: "center",
  },

  headerContent: {
    flex: 1,
    marginLeft: 16,
  },

  title: {
    fontSize: 18,
    fontWeight: "800",
    color: "#0F172A",
  },

  subtitle: {
    marginTop: 4,

    fontSize: 13,

    color: "#64748B",

    fontWeight: "600",
  },

  divider: {
    height: 1,

    backgroundColor: "#EEF2F7",

    marginVertical: 18,
  },

  row: {
    flexDirection: "row",

    alignItems: "center",

    marginBottom: 18,
  },

  info: {
    marginLeft: 14,
    flex: 1,
  },

  label: {
    fontSize: 13,

    color: "#94A3B8",

    fontWeight: "600",
  },

  value: {
    marginTop: 4,

    fontSize: 16,

    fontWeight: "700",

    color: "#0F172A",
  },

  bottom: {
    marginTop: 10,

    flexDirection: "row",

    justifyContent: "space-between",

    alignItems: "center",
  },

  statusBadge: {
    paddingHorizontal: 14,
    paddingVertical: 8,

    borderRadius: 25,
  },

  statusText: {
    fontWeight: "800",

    fontSize: 13,
  },

  button: {
    flexDirection: "row",

    alignItems: "center",

    backgroundColor: "#173B8C",

    paddingHorizontal: 18,
    paddingVertical: 11,

    borderRadius: 14,

    shadowColor: "#173B8C",
    shadowOpacity: 0.25,
    shadowRadius: 8,
    shadowOffset: {
      width: 0,
      height: 4,
    },

    elevation: 3,
  },

  buttonText: {
    marginLeft: 8,

    color: "#FFFFFF",

    fontWeight: "700",

    fontSize: 14,
  },
});