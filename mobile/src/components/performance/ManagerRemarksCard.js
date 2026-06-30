import React from "react";
import {
  View,
  Text,
 StyleSheet,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

export default function ManagerRemarksCard({
  managerName,
  designation,
  remarks,
}) {
  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View style={styles.iconContainer}>
          <Ionicons
            name="chatbubble-ellipses-outline"
            size={24}
            color="#173B8C"
          />
        </View>

        <View style={styles.headerText}>
          <Text style={styles.title}>
            Manager Remarks
          </Text>

          <Text style={styles.manager}>
            {managerName}
          </Text>

          <Text style={styles.designation}>
            {designation}
          </Text>
        </View>
      </View>

      <View style={styles.divider} />

      <Text style={styles.remarks}>
        "{remarks}"
      </Text>

      <View style={styles.footer}>
        <View style={styles.tag}>
          <Ionicons
            name="checkmark-circle"
            size={16}
            color="#16A34A"
          />

          <Text style={styles.tagText}>
            Reviewed
          </Text>
        </View>

        <Text style={styles.date}>
          Updated Today
        </Text>
      </View>
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
  },

  iconContainer: {
    width: 56,
    height: 56,

    borderRadius: 16,

    backgroundColor: "#EEF4FF",

    justifyContent: "center",
    alignItems: "center",
  },

  headerText: {
    flex: 1,
    marginLeft: 16,
  },

  title: {
    fontSize: 18,
    fontWeight: "800",
    color: "#0F172A",
  },

  manager: {
    marginTop: 5,

    fontSize: 15,

    fontWeight: "700",

    color: "#173B8C",
  },

  designation: {
    marginTop: 2,

    fontSize: 13,

    color: "#64748B",

    fontWeight: "600",
  },

  divider: {
    height: 1,

    backgroundColor: "#EEF2F7",

    marginVertical: 18,
  },

  remarks: {
    fontSize: 15,

    color: "#475569",

    lineHeight: 26,

    fontWeight: "500",

    fontStyle: "italic",
  },

  footer: {
    marginTop: 20,

    flexDirection: "row",

    justifyContent: "space-between",

    alignItems: "center",
  },

  tag: {
    flexDirection: "row",
    alignItems: "center",

    backgroundColor: "#ECFDF5",

    paddingHorizontal: 12,
    paddingVertical: 7,

    borderRadius: 20,
  },

  tagText: {
    marginLeft: 6,

    color: "#16A34A",

    fontWeight: "700",

    fontSize: 13,
  },

  date: {
    fontSize: 13,

    color: "#94A3B8",

    fontWeight: "600",
  },
});