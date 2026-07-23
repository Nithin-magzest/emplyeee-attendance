import React from "react";
import {
  TouchableOpacity,
  View,
  Text,
  StyleSheet,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

import THEME from "../../constants/theme";

export default function QuickActionCard({
  title,
  subtitle,
  icon,
  iconColor,
  iconBackground,
  onPress,
}) {
  return (
    <TouchableOpacity
      activeOpacity={0.85}
      style={styles.card}
      onPress={onPress}
    >
      <View
        style={[
          styles.iconContainer,
          {
            backgroundColor:
              iconBackground,
          },
        ]}
      >
        <Ionicons
          name={icon}
          size={24}
          color={iconColor}
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

      <Ionicons
        name="chevron-forward"
        size={20}
        color={THEME.colors.textLight}
      />
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor:
      THEME.colors.card,

    borderRadius:
      THEME.radius.card,

    borderWidth: 1,

    borderColor:
      THEME.colors.border,

    padding:
      THEME.spacing.cardPadding,

    flexDirection: "row",

    alignItems: "center",

    marginBottom:
      THEME.spacing.cardGap,

    ...THEME.shadows.sm,
  },

  iconContainer: {
    width: 52,

    height: 52,

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

    color:
      THEME.colors.text,
  },

  subtitle: {
    marginTop: 4,

    ...THEME.typography.caption,

    color:
      THEME.colors.textSecondary,
  },
});