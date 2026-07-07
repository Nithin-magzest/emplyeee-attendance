import React from "react";
import {
  View,
  Text,
  StyleSheet,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

export default function AttendanceOverviewCard({

  present = 228,

  absent = 18,

  late = 8,

  onLeave = 6,

}) {

  const total =
    present +
    absent +
    late +
    onLeave;

  const percentage = Math.round(
    (present / total) * 100
  );

  const data = [
    {
      label: "Present",
      value: present,
      icon: "checkmark-circle",
      color: "#22C55E",
      bg: "#ECFDF5",
    },
    {
      label: "Absent",
      value: absent,
      icon: "close-circle",
      color: "#EF4444",
      bg: "#FEF2F2",
    },
    {
      label: "Late",
      value: late,
      icon: "time",
      color: "#F59E0B",
      bg: "#FFFBEB",
    },
    {
      label: "On Leave",
      value: onLeave,
      icon: "airplane",
      color: "#2563EB",
      bg: "#EFF6FF",
    },
  ];

  return (

    <View style={styles.card}>

      <View style={styles.header}>

        <View>

          <Text style={styles.title}>
            Today's Attendance
          </Text>

          <Text style={styles.subtitle}>
            Live workforce status
          </Text>

        </View>

        <View style={styles.scoreBox}>

          <Text style={styles.score}>
            {percentage}%
          </Text>

          <Text style={styles.scoreLabel}>
            Present
          </Text>

        </View>

      </View>

      <View style={styles.progressTrack}>

        <View
          style={[
            styles.progressFill,
            {
              width: `${percentage}%`,
            },
          ]}
        />

      </View>

      <View style={styles.list}>

        {data.map((item) => (

          <View
            key={item.label}
            style={styles.row}
          >

            <View
              style={styles.left}
            >

              <View
                style={[
                  styles.iconBox,
                  {
                    backgroundColor:
                      item.bg,
                  },
                ]}
              >

                <Ionicons
                  name={item.icon}
                  size={18}
                  color={item.color}
                />

              </View>

              <Text style={styles.label}>
                {item.label}
              </Text>

            </View>

            <Text style={styles.value}>
              {item.value}
            </Text>

          </View>

        ))}

      </View>

    </View>

  );

}

const styles = StyleSheet.create({

  card: {

    backgroundColor: "#FFFFFF",

    borderRadius: 26,

    padding: 22,

    marginBottom: 26,

    borderWidth: 1,

    borderColor: "#EDF2F7",

    shadowColor: "#0F172A",

    shadowOpacity: 0.07,

    shadowRadius: 18,

    shadowOffset: {
      width: 0,
      height: 8,
    },

    elevation: 6,

  },

  header: {

    flexDirection: "row",

    justifyContent: "space-between",

    alignItems: "center",

    marginBottom: 20,

  },

  title: {

    fontSize: 21,

    fontWeight: "800",

    color: "#0F172A",

  },

  subtitle: {

    marginTop: 4,

    fontSize: 13,

    color: "#64748B",

  },

  scoreBox: {

    alignItems: "center",

  },

  score: {

    fontSize: 34,

    fontWeight: "800",

    color: "#2563EB",

  },

  scoreLabel: {

    fontSize: 12,

    color: "#64748B",

    fontWeight: "600",

  },

  progressTrack: {

    height: 10,

    borderRadius: 8,

    backgroundColor: "#EEF2F7",

    overflow: "hidden",

    marginBottom: 24,

  },

  progressFill: {

    height: "100%",

    backgroundColor: "#2563EB",

    borderRadius: 8,

  },

  list: {

    gap: 14,

  },

  row: {

    flexDirection: "row",

    justifyContent: "space-between",

    alignItems: "center",

  },

  left: {

    flexDirection: "row",

    alignItems: "center",

  },

  iconBox: {

    width: 42,

    height: 42,

    borderRadius: 12,

    justifyContent: "center",

    alignItems: "center",

    marginRight: 14,

  },

  label: {

    fontSize: 15,

    fontWeight: "600",

    color: "#334155",

  },

  value: {

    fontSize: 20,

    fontWeight: "800",

    color: "#0F172A",

  },

});