import React from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";

export default function DocumentCard({
  title = "Aadhaar Card",
  number = "XXXX XXXX 4589",
  status = "Verified",
  uploadedOn = "12 Jun 2026",
  icon = "document-text-outline",
  onView = () => {},
  onDownload = () => {},
}) {
  const verified = status === "Verified";

  return (
    <View style={styles.card}>
      {/* Top */}

      <View style={styles.header}>
        <View style={styles.left}>
          <View style={styles.iconBox}>
            <Ionicons
              name={icon}
              size={22}
              color="#173B8C"
            />
          </View>

          <View style={styles.info}>
            <Text style={styles.title}>
              {title}
            </Text>

            <Text style={styles.number}>
              {number}
            </Text>
          </View>
        </View>

        <View
          style={[
            styles.badge,
            verified
              ? styles.verified
              : styles.pending,
          ]}
        >
          <View
            style={[
              styles.dot,
              {
                backgroundColor: verified
                  ? "#22C55E"
                  : "#F59E0B",
              },
            ]}
          />

          <Text
            style={[
              styles.badgeText,
              {
                color: verified
                  ? "#15803D"
                  : "#B45309",
              },
            ]}
          >
            {status}
          </Text>
        </View>
      </View>

      {/* Divider */}

      <View style={styles.divider} />

      {/* Footer */}

      <View style={styles.footer}>
        <View>
          <Text style={styles.uploadLabel}>
            Uploaded
          </Text>

          <Text style={styles.uploadDate}>
            {uploadedOn}
          </Text>
        </View>

        <View style={styles.actions}>
          <TouchableOpacity
            style={styles.actionButton}
            onPress={onView}
          >
            <Ionicons
              name="eye-outline"
              size={20}
              color="#173B8C"
            />
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.actionButton}
            onPress={onDownload}
          >
            <Ionicons
              name="download-outline"
              size={20}
              color="#173B8C"
            />
          </TouchableOpacity>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#FFFFFF",

    borderRadius: 20,

    padding: 18,

    marginBottom: 16,

    borderWidth: 1,

    borderColor: "#E8EDF3",

    shadowColor: "#0F172A",

    shadowOpacity: 0.04,

    shadowRadius: 10,

    shadowOffset: {
      width: 0,
      height: 4,
    },

    elevation: 2,
  },

  header: {
    flexDirection: "row",

    justifyContent: "space-between",

    alignItems: "center",
  },

  left: {
    flexDirection: "row",

    flex: 1,

    alignItems: "center",
  },

  iconBox: {
    width: 52,

    height: 52,

    borderRadius: 16,

    backgroundColor: "#EEF4FF",

    justifyContent: "center",

    alignItems: "center",
  },

  info: {
    marginLeft: 14,

    flex: 1,
  },

  title: {
    fontSize: 16,

    fontWeight: "700",

    color: "#0F172A",
  },

  number: {
    marginTop: 4,

    fontSize: 13,

    color: "#64748B",

    fontWeight: "500",
  },

  badge: {
    flexDirection: "row",

    alignItems: "center",

    paddingHorizontal: 10,

    paddingVertical: 6,

    borderRadius: 20,
  },

  verified: {
    backgroundColor: "#ECFDF5",
  },

  pending: {
    backgroundColor: "#FEF3C7",
  },

  dot: {
    width: 8,

    height: 8,

    borderRadius: 4,

    marginRight: 6,
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

  footer: {
    flexDirection: "row",

    justifyContent: "space-between",

    alignItems: "center",
  },

  uploadLabel: {
    fontSize: 11,

    color: "#94A3B8",

    fontWeight: "600",
  },

  uploadDate: {
    marginTop: 4,

    fontSize: 14,

    color: "#334155",

    fontWeight: "700",
  },

  actions: {
    flexDirection: "row",
  },

  actionButton: {
    width: 42,

    height: 42,

    borderRadius: 12,

    backgroundColor: "#F8FAFC",

    borderWidth: 1,

    borderColor: "#E2E8F0",

    justifyContent: "center",

    alignItems: "center",

    marginLeft: 10,
  },
});