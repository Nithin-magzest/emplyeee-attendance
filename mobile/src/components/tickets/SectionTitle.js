import React from "react";
import {
  View,
  Text,
  StyleSheet,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

export default function SectionTitle({
  title,
  subtitle = "",
  icon = "ellipse-outline",
}) {
  return (
    <View style={styles.container}>
      <View style={styles.left}>
        <View style={styles.iconContainer}>
          <Ionicons
            name={icon}
            size={20}
            color="#173B8C"
          />
        </View>

        <View>
          <Text style={styles.title}>
            {title}
          </Text>

          {subtitle !== "" && (
            <Text style={styles.subtitle}>
              {subtitle}
            </Text>
          )}
        </View>
      </View>

      <View style={styles.line} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginTop: 12,
    marginBottom: 18,
  },

  left: {
    flexDirection: "row",
    alignItems: "center",
  },

  iconContainer: {
    width: 42,
    height: 42,

    borderRadius: 21,

    backgroundColor: "#EEF4FF",

    justifyContent: "center",
    alignItems: "center",

    marginRight: 14,
  },

  title: {
    fontSize: 20,
    fontWeight: "800",
    color: "#0F172A",
  },

  subtitle: {
    marginTop: 3,

    fontSize: 13,

    color: "#64748B",

    fontWeight: "500",
  },

  line: {
    marginTop: 16,

    height: 1,

    backgroundColor: "#E2E8F0",
  },
});