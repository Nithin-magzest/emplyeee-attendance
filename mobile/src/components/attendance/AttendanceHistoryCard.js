import React from "react";
import {
  View,
  Text,
  StyleSheet,
  FlatList,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";

const STATUS = {
  Present: {
    color: "#16A34A",
    bg: "#ECFDF5",
    icon: "checkmark-circle",
  },
  Late: {
    color: "#D97706",
    bg: "#FFFBEB",
    icon: "time",
  },
  Absent: {
    color: "#DC2626",
    bg: "#FEF2F2",
    icon: "close-circle",
  },
  Holiday: {
    color: "#7C3AED",
    bg: "#F5F3FF",
    icon: "gift",
  },
  "Half Day": {
    color: "#EA580C",
    bg: "#FFF7ED",
    icon: "sunny",
  },
};

export default function AttendanceHistoryCard({
  records = [],
}) {
  const renderItem = ({ item }) => {
    const status =
      STATUS[item.status] || {
        color: "#64748B",
        bg: "#F8FAFC",
        icon: "ellipse",
      };

    const date = new Date(item.date);

    return (
      <View style={styles.card}>
        {/* Date */}

        <View style={styles.dateBox}>
          <Text style={styles.day}>
            {date.getDate()}
          </Text>

          <Text style={styles.month}>
            {date.toLocaleString("default", {
              month: "short",
            })}
          </Text>
        </View>

        {/* Content */}

        <View style={styles.content}>
          <View style={styles.topRow}>
            <Text style={styles.dateTitle}>
              {date.toLocaleDateString(undefined, {
                weekday: "long",
              })}
            </Text>

            <View
              style={[
                styles.statusBadge,
                {
                  backgroundColor: status.bg,
                },
              ]}
            >
              <Ionicons
                name={status.icon}
                size={14}
                color={status.color}
              />

              <Text
                style={[
                  styles.statusText,
                  {
                    color: status.color,
                  },
                ]}
              >
                {item.status}
              </Text>
            </View>
          </View>

          <View style={styles.timeline}>
            <View style={styles.timelineItem}>
              <Ionicons
                name="log-in-outline"
                size={18}
                color="#16A34A"
              />

              <Text style={styles.label}>
                In
              </Text>

              <Text style={styles.value}>
                {item.check_in || "--:--"}
              </Text>
            </View>

            <View style={styles.timelineDivider} />

            <View style={styles.timelineItem}>
              <Ionicons
                name="log-out-outline"
                size={18}
                color="#DC2626"
              />

              <Text style={styles.label}>
                Out
              </Text>

              <Text style={styles.value}>
                {item.check_out || "--:--"}
              </Text>
            </View>

            <View style={styles.timelineDivider} />

            <View style={styles.timelineItem}>
              <Ionicons
                name="time-outline"
                size={18}
                color="#173B8C"
              />

              <Text style={styles.label}>
                Hours
              </Text>

              <Text style={styles.value}>
                {item.hours || "--"}
              </Text>
            </View>
          </View>
        </View>
      </View>
    );
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View>
          <Text style={styles.heading}>
            Attendance History
          </Text>

          <Text style={styles.subtitle}>
            Daily attendance records
          </Text>
        </View>

        <Ionicons
          name="time-outline"
          size={22}
          color="#173B8C"
        />
      </View>

      <FlatList
        scrollEnabled={false}
        data={records}
        keyExtractor={(item, index) =>
          item.date + index
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
    marginTop: 24,
    marginBottom: 20,
  },

  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 18,
  },

  heading: {
    fontSize: 20,
    fontWeight: "800",
    color: "#0F172A",
  },

  subtitle: {
    marginTop: 4,
    fontSize: 13,
    color: "#64748B",
    fontWeight: "600",
  },

  card: {
    backgroundColor: "#FFFFFF",
    borderRadius: 22,
    padding: 18,
    flexDirection: "row",

    borderWidth: 1,
    borderColor: "#E8EDF5",

    shadowColor: "#0F172A",
    shadowOpacity: 0.05,
    shadowRadius: 12,
    shadowOffset: {
      width: 0,
      height: 5,
    },

    elevation: 4,
  },

  dateBox: {
    width: 68,
    height: 68,
    borderRadius: 18,
    backgroundColor: "#EEF4FF",
    justifyContent: "center",
    alignItems: "center",
  },

  day: {
    fontSize: 24,
    fontWeight: "800",
    color: "#173B8C",
  },

  month: {
    marginTop: 2,
    fontSize: 12,
    fontWeight: "700",
    color: "#64748B",
  },

  content: {
    flex: 1,
    marginLeft: 18,
  },

  topRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },

  dateTitle: {
    fontSize: 16,
    fontWeight: "700",
    color: "#0F172A",
  },

  statusBadge: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 18,
  },

  statusText: {
    marginLeft: 5,
    fontSize: 12,
    fontWeight: "700",
  },

  timeline: {
    marginTop: 18,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },

  timelineItem: {
    flex: 1,
    alignItems: "center",
  },

  timelineDivider: {
    width: 1,
    height: 42,
    backgroundColor: "#E5E7EB",
  },

  label: {
    marginTop: 6,
    fontSize: 12,
    color: "#64748B",
  },

  value: {
    marginTop: 3,
    fontSize: 15,
    fontWeight: "800",
    color: "#0F172A",
  },
});