import React from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";

export default function SectionHeader({
  title = "Section Title",
  subtitle = "",
  actionText = "",
  onPress,
}) {
  return (
    <View style={styles.container}>
      <View style={styles.left}>
        <Text style={styles.title}>
          {title}
        </Text>

        {subtitle ? (
          <Text style={styles.subtitle}>
            {subtitle}
          </Text>
        ) : null}
      </View>

      {actionText ? (
        <TouchableOpacity
          activeOpacity={0.85}
          style={styles.actionButton}
          onPress={onPress}
        >
          <Text style={styles.actionText}>
            {actionText}
          </Text>

          <Ionicons
            name="chevron-forward"
            size={16}
            color="#173B8C"
          />
        </TouchableOpacity>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginTop: 8,
    marginBottom: 18,

    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },

  left: {
    flex: 1,
  },

  title: {
    fontSize: 20,
    fontWeight: "800",
    color: "#0F172A",
    letterSpacing: -0.4,
  },

  subtitle: {
    marginTop: 4,

    fontSize: 13,

    color: "#64748B",

    lineHeight: 18,
  },

  actionButton: {
    flexDirection: "row",
    alignItems: "center",

    backgroundColor: "#EEF4FF",

    paddingHorizontal: 14,
    paddingVertical: 8,

    borderRadius: 12,
  },

  actionText: {
    marginRight: 4,

    color: "#173B8C",

    fontSize: 13,

    fontWeight: "700",
  },
});