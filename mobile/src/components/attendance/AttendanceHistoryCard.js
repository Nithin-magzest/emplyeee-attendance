import React from "react";
import {
  View,
  Text,
  StyleSheet,
  FlatList,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";

const STATUS_COLORS = {
  Present: "#22C55E",
  Absent: "#EF4444",
  Late: "#F59E0B",
  "Half Day": "#FB923C",
  Holiday: "#8B5CF6",
};

export default function AttendanceHistoryCard({
  records = [],
}) {
  const renderItem = ({ item }) => {
    const color =
      STATUS_COLORS[item.status] || "#94A3B8";

    return (
      <View style={styles.card}>
        {/* Left Date */}

        <View style={styles.dateContainer}>
          <Text style={styles.day}>
            {new Date(item.date).getDate()}
          </Text>

          <Text style={styles.month}>
            {new Date(item.date).toLocaleString(
              "default",
              {
                month: "short",
              }
            )}
          </Text>
        </View>

        {/* Details */}

        <View style={styles.details}>
          <View style={styles.row}>
            <Ionicons
              name="log-in-outline"
              size={16}
              color="#173B8C"
            />

            <Text style={styles.time}>
              {item.check_in || "--:--"}
            </Text>

            <Ionicons
              name="log-out-outline"
              size={16}
              color="#173B8C"
              style={{ marginLeft: 18 }}
            />

            <Text style={styles.time}>
              {item.check_out || "--:--"}
            </Text>
          </View>

          <View style={styles.bottomRow}>
            <Text style={styles.hours}>
              {item.hours || "--"} hrs
            </Text>

            <View
              style={[
                styles.badge,
                {
                  backgroundColor:
                    color + "20",
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
        </View>
      </View>
    );
  };

  return (
    <View style={styles.container}>
      <Text style={styles.heading}>
        Attendance History
      </Text>

      <FlatList
        scrollEnabled={false}
        data={records}
        keyExtractor={(item, index) =>
          item.date + index
        }
        renderItem={renderItem}
        ItemSeparatorComponent={() => (
          <View style={{ height: 14 }} />
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

  heading: {
    fontSize: 20,
    fontWeight: "800",
    color: "#0F172A",
    marginBottom: 18,
  },

  card: {
    backgroundColor: "#FFFFFF",

    borderRadius: 20,

    padding: 18,

    flexDirection: "row",

    alignItems: "center",

    shadowColor: "#000",
    shadowOpacity: 0.05,
    shadowRadius: 10,
    shadowOffset: {
      width: 0,
      height: 5,
    },

    elevation: 4,
  },

  dateContainer: {
    width: 65,
    height: 65,

    borderRadius: 18,

    backgroundColor: "#EEF4FF",

    justifyContent: "center",
    alignItems: "center",
  },

  day: {
    fontSize: 22,
    fontWeight: "800",
    color: "#173B8C",
  },

  month: {
    fontSize: 12,
    fontWeight: "700",
    color: "#64748B",
    marginTop: 2,
  },

  details: {
    flex: 1,
    marginLeft: 18,
  },

  row: {
    flexDirection: "row",
    alignItems: "center",
  },

  time: {
    marginLeft: 6,
    color: "#0F172A",
    fontWeight: "700",
    fontSize: 14,
  },

  bottomRow: {
    marginTop: 14,

    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },

  hours: {
    color: "#64748B",
    fontWeight: "600",
    fontSize: 14,
  },

  badge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
  },

  badgeText: {
    fontSize: 12,
    fontWeight: "700",
  },
});