import React from "react";
import {
  View,
  Text,
  StyleSheet,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

import THEME from "../../constants/theme";

export default function ActivityCard({
  icon,
  iconColor,
  iconBackground,
  title,
  description,
  time,
}) {
  return (
    <View style={styles.card}>
      {/* Icon */}

      <View
        style={[
          styles.iconContainer,
          {
            backgroundColor: iconBackground,
          },
        ]}
      >
        <Ionicons
          name={icon}
          size={22}
          color={iconColor}
        />
      </View>

      {/* Content */}

      <View style={styles.content}>
        <Text style={styles.title}>
          {title}
        </Text>

        <Text style={styles.description}>
          {description}
        </Text>

        <Text style={styles.time}>
          {time}
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flexDirection: "row",

    alignItems: "flex-start",

    backgroundColor: THEME.colors.card,

    borderRadius: THEME.radius.card,

    padding: THEME.spacing.cardPadding,

    borderWidth: 1,

    borderColor: THEME.colors.border,

    marginBottom: THEME.spacing.cardGap,

    ...THEME.shadows.sm,
  },

  iconContainer: {
    width: 48,

    height: 48,

    borderRadius: 14,

    justifyContent: "center",

    alignItems: "center",
  },

  content: {
    flex: 1,

    marginLeft: 16,
  },

  title: {
    ...THEME.typography.cardTitle,

    color: THEME.colors.text,
  },

  description: {
    marginTop: 6,

    ...THEME.typography.body,

    color: THEME.colors.textSecondary,
  },

  time: {
    marginTop: 10,

    ...THEME.typography.caption,

    color: THEME.colors.textLight,
  },
});