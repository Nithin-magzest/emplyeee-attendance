import React from "react";
import {
  View,
  Text,
  StyleSheet,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";

export default function PendingCard({
  pendingLeaves = 0,
  pendingResignations = 0,
}) {

  if (
    pendingLeaves === 0 &&
    pendingResignations === 0
  ) {
    return null;
  }

  return (
    <View style={styles.card}>

      <View style={styles.header}>

        <View style={styles.iconBox}>

          <Ionicons
            name="notifications"
            size={22}
            color="#D97706"
          />

        </View>

        <View style={{ flex: 1 }}>

          <Text style={styles.title}>
            Pending Approvals
          </Text>

          <Text style={styles.subtitle}>
            Action required from administrator
          </Text>

        </View>

      </View>

      {pendingLeaves > 0 && (

        <View style={styles.row}>

          <View style={styles.left}>

            <View
              style={[
                styles.circle,
                {
                  backgroundColor: "#EEF4FF",
                },
              ]}
            >

              <Ionicons
                name="document-text"
                size={18}
                color="#2563EB"
              />

            </View>

            <View>

              <Text style={styles.rowTitle}>
                Leave Requests
              </Text>

              <Text style={styles.rowSub}>
                Waiting for approval
              </Text>

            </View>

          </View>

          <View style={styles.countBadge}>

            <Text style={styles.count}>
              {pendingLeaves}
            </Text>

          </View>

        </View>

      )}

      {pendingResignations > 0 && (

        <View style={styles.row}>

          <View style={styles.left}>

            <View
              style={[
                styles.circle,
                {
                  backgroundColor: "#FEF2F2",
                },
              ]}
            >

              <Ionicons
                name="exit-outline"
                size={18}
                color="#DC2626"
              />

            </View>

            <View>

              <Text style={styles.rowTitle}>
                Resignations
              </Text>

              <Text style={styles.rowSub}>
                Waiting for review
              </Text>

            </View>

          </View>

          <View
            style={[
              styles.countBadge,
              {
                backgroundColor: "#FEE2E2",
              },
            ]}
          >

            <Text
              style={[
                styles.count,
                {
                  color: "#DC2626",
                },
              ]}
            >
              {pendingResignations}
            </Text>

          </View>

        </View>

      )}

    </View>
  );
}

const styles = StyleSheet.create({

  card: {

    backgroundColor: "#FFFFFF",

    borderRadius: 22,

    padding: 20,

    marginBottom: 24,

    shadowColor: "#000",

    shadowOpacity: 0.05,

    shadowRadius: 12,

    shadowOffset: {
      width: 0,
      height: 5,
    },

    elevation: 5,

    borderWidth: 1,

    borderColor: "#EEF2F7",

  },

  header: {

    flexDirection: "row",

    alignItems: "center",

    marginBottom: 20,

  },

  iconBox: {

    width: 50,

    height: 50,

    borderRadius: 15,

    backgroundColor: "#FFF7ED",

    justifyContent: "center",

    alignItems: "center",

    marginRight: 14,

  },

  title: {

    fontSize: 18,

    fontWeight: "700",

    color: "#111827",

  },

  subtitle: {

    marginTop: 4,

    color: "#64748B",

    fontSize: 13,

  },

  row: {

    flexDirection: "row",

    justifyContent: "space-between",

    alignItems: "center",

    paddingVertical: 12,

  },

  left: {

    flexDirection: "row",

    alignItems: "center",

  },

  circle: {

    width: 44,

    height: 44,

    borderRadius: 14,

    justifyContent: "center",

    alignItems: "center",

    marginRight: 14,

  },

  rowTitle: {

    fontSize: 15,

    fontWeight: "700",

    color: "#111827",

  },

  rowSub: {

    marginTop: 3,

    color: "#64748B",

    fontSize: 12,

  },

  countBadge: {

    minWidth: 36,

    height: 36,

    borderRadius: 18,

    backgroundColor: "#DBEAFE",

    justifyContent: "center",

    alignItems: "center",

    paddingHorizontal: 10,

  },

  count: {

    color: "#2563EB",

    fontWeight: "700",

    fontSize: 15,

  },

});