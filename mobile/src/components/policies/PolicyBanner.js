import React from "react";
import {
  View,
  Text,
  StyleSheet,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

export default function PolicyBanner({
  type = "info",
  title,
  message,
}) {
  const getTheme = () => {
    switch (type) {
      case "success":
        return {
          background: "#ECFDF5",
          border: "#22C55E",
          icon: "checkmark-circle",
          color: "#15803D",
        };

      case "warning":
        return {
          background: "#FFF7ED",
          border: "#F59E0B",
          icon: "warning",
          color: "#B45309",
        };

      case "danger":
        return {
          background: "#FEF2F2",
          border: "#EF4444",
          icon: "alert-circle",
          color: "#DC2626",
        };

      case "primary":
        return {
          background: "#EEF4FF",
          border: "#173B8C",
          icon: "shield-checkmark",
          color: "#173B8C",
        };

      default:
        return {
          background: "#F8FAFC",
          border: "#CBD5E1",
          icon: "information-circle",
          color: "#475569",
        };
    }
  };

  const theme = getTheme();

  return (
    <View
      style={[
        styles.container,
        {
          backgroundColor: theme.background,
          borderLeftColor: theme.border,
        },
      ]}
    >
      <View
        style={[
          styles.iconContainer,
          {
            backgroundColor: "#FFFFFF",
          },
        ]}
      >
        <Ionicons
          name={theme.icon}
          size={24}
          color={theme.color}
        />
      </View>

      <View style={styles.content}>
        <Text
          style={[
            styles.title,
            {
              color: theme.color,
            },
          ]}
        >
          {title}
        </Text>

        <Text style={styles.message}>
          {message}
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",

    alignItems: "flex-start",

    borderLeftWidth: 5,

    borderRadius: 20,

    padding: 18,

    marginBottom: 22,

    shadowColor: "#000",
    shadowOpacity: 0.04,
    shadowRadius: 8,
    shadowOffset: {
      width: 0,
      height: 4,
    },

    elevation: 2,
  },

  iconContainer: {
    width: 52,
    height: 52,

    borderRadius: 16,

    justifyContent: "center",
    alignItems: "center",

    marginRight: 16,
  },

  content: {
    flex: 1,
  },

  title: {
    fontSize: 18,

    fontWeight: "800",

    marginBottom: 8,
  },

  message: {
    fontSize: 14,

    lineHeight: 23,

    color: "#475569",

    fontWeight: "500",
  },
});