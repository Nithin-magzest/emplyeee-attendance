import React from "react";
import {
  View,
  Text,
  StyleSheet,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

export default function AchievementCard({
  title,
  subtitle,
  icon,
  color,
  background,
}) {
  return (
    <View style={styles.container}>
      <View
        style={[
          styles.iconContainer,
          {
            backgroundColor: background,
          },
        ]}
      >
        <Ionicons
          name={icon}
          size={28}
          color={color}
        />
      </View>

      <View style={styles.content}>
        <Text style={styles.title}>
          {title}
        </Text>

        <Text style={styles.subtitle}>
          {subtitle}
        </Text>
      </View>

      <View
        style={[
          styles.badge,
          {
            backgroundColor: background,
          },
        ]}
      >
        <Ionicons
          name="checkmark-circle"
          size={18}
          color={color}
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: "#FFFFFF",

    borderRadius: 22,

    padding: 18,

    flexDirection: "row",

    alignItems: "center",

    marginBottom: 16,

    borderWidth: 1,
    borderColor: "#E8EDF3",

    shadowColor: "#000",
    shadowOpacity: 0.04,
    shadowRadius: 10,
    shadowOffset: {
      width: 0,
      height: 5,
    },

    elevation: 2,
  },

  iconContainer: {
    width: 60,
    height: 60,

    borderRadius: 18,

    justifyContent: "center",
    alignItems: "center",
  },

  content: {
    flex: 1,

    marginLeft: 16,
  },

  title: {
    fontSize: 17,

    fontWeight: "800",

    color: "#0F172A",
  },

  subtitle: {
    marginTop: 5,

    fontSize: 14,

    color: "#64748B",

    lineHeight: 20,

    fontWeight: "500",
  },

  badge: {
    width: 38,
    height: 38,

    borderRadius: 19,

    justifyContent: "center",
    alignItems: "center",
  },
});