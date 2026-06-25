import React from "react";
import {
  View,
  Text,
  StyleSheet,
  FlatList,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";

const STATUS_COLORS = {
  Approved: "#16A34A",
  Pending: "#F59E0B",
  Rejected: "#DC2626",
};

export default function OvertimeHistoryCard({
  records = [],
}) {
  const renderItem = ({ item }) => {
    const color =
      STATUS_COLORS[item.status] || "#64748B";

    return (
      <View style={styles.card}>
        {/* Top */}

        <View style={styles.header}>
          <View>
            <Text style={styles.date}>
              {item.date}
            </Text>

            <Text style={styles.day}>
              {item.day}
            </Text>
          </View>

          <View
            style={[
              styles.badge,
              {
                backgroundColor: color + "18",
              },
            ]}
          >
            <Text
              style={[
                styles.badgeText,
                {
                  color,
                },
              ]}
            >
              {item.status}
            </Text>
          </View>
        </View>

        <View style={styles.divider} />

        {/* Details */}

        <View style={styles.row}>
          <View style={styles.info}>
            <Ionicons
              name="time-outline"
              size={18}
              color="#173B8C"
            />

            <Text style={styles.label}>
              OT Hours
            </Text>
          </View>

          <Text style={styles.value}>
            {item.hours}
          </Text>
        </View>

        <View style={styles.row}>
          <View style={styles.info}>
            <Ionicons
              name="calendar-outline"
              size={18}
              color="#173B8C"
            />

            <Text style={styles.label}>
              Comp-off Earned
            </Text>
          </View>

          <Text style={styles.value}>
            {item.compOff}
          </Text>
        </View>

        <View style={styles.row}>
          <View style={styles.info}>
            <Ionicons
              name="person-outline"
              size={18}
              color="#173B8C"
            />

            <Text style={styles.label}>
              Approved By
            </Text>
          </View>

          <Text style={styles.value}>
            {item.approvedBy}
          </Text>
        </View>
      </View>
    );
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>
        Overtime Records
      </Text>

      <Text style={styles.subtitle}>
        Your approved overtime history
      </Text>

      <FlatList
        data={records}
        scrollEnabled={false}
        keyExtractor={(item, index) =>
          index.toString()
        }
        renderItem={renderItem}
        ItemSeparatorComponent={() => (
          <View style={{ height: 16 }} />
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginBottom: 24,
  },

  title: {
    fontSize: 22,
    fontWeight: "800",
    color: "#0F172A",
  },

  subtitle: {
    marginTop: 4,
    marginBottom: 18,

    color: "#64748B",

    fontSize: 13,
  },

  card: {
    backgroundColor: "#FFFFFF",

    borderRadius: 22,

    padding: 20,

    borderWidth: 1,

    borderColor: "#E9EEF5",

    shadowColor: "#000",

    shadowOpacity: 0.05,

    shadowRadius: 14,

    shadowOffset: {
      width: 0,
      height: 6,
    },

    elevation: 4,
  },

  header: {
    flexDirection: "row",

    justifyContent: "space-between",

    alignItems: "center",
  },

  date: {
    fontSize: 18,

    fontWeight: "800",

    color: "#0F172A",
  },

  day: {
    marginTop: 4,

    color: "#64748B",

    fontSize: 13,
  },

  badge: {
    paddingHorizontal: 12,

    paddingVertical: 6,

    borderRadius: 20,
  },

  badgeText: {
    fontWeight: "700",

    fontSize: 12,
  },

  divider: {
    height: 1,

    backgroundColor: "#EEF2F7",

    marginVertical: 18,
  },

  row: {
    flexDirection: "row",

    justifyContent: "space-between",

    alignItems: "center",

    marginBottom: 16,
  },

  info: {
    flexDirection: "row",

    alignItems: "center",
  },

  label: {
    marginLeft: 10,

    color: "#64748B",

    fontSize: 14,

    fontWeight: "600",
  },

  value: {
    fontSize: 15,

    fontWeight: "800",

    color: "#0F172A",
  },
});