import React from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

export default function PolicyCategoryCard({
  icon = "document-text-outline",
  title,
  description,
  color = "#173B8C",
  background = "#EEF4FF",
  onPress = () => {},
}) {
  return (
    <TouchableOpacity
      activeOpacity={0.9}
      style={styles.container}
      onPress={onPress}
    >
      {/* Left Section */}

      <View style={styles.left}>
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
            size={26}
            color={color}
          />
        </View>

        <View style={styles.textContainer}>
          <Text style={styles.title}>
            {title}
          </Text>

          <Text style={styles.description}>
            {description}
          </Text>
        </View>
      </View>

      {/* Right Arrow */}

      <Ionicons
        name="chevron-forward"
        size={22}
        color="#94A3B8"
      />
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: "#FFFFFF",

    borderRadius: 22,

    padding: 18,

    marginBottom: 18,

    borderWidth: 1,
    borderColor: "#E8EDF3",

    flexDirection: "row",

    justifyContent: "space-between",

    alignItems: "center",

    shadowColor: "#0F172A",
    shadowOpacity: 0.05,
    shadowRadius: 10,
    shadowOffset: {
      width: 0,
      height: 5,
    },

    elevation: 3,
  },

  left: {
    flexDirection: "row",

    alignItems: "center",

    flex: 1,
  },

  iconContainer: {
    width: 58,
    height: 58,

    borderRadius: 18,

    justifyContent: "center",

    alignItems: "center",
  },

  textContainer: {
    flex: 1,

    marginLeft: 16,
  },

  title: {
    fontSize: 17,

    fontWeight: "800",

    color: "#0F172A",

    marginBottom: 6,
  },

  description: {
    fontSize: 14,

    color: "#64748B",

    lineHeight: 21,
  },
});