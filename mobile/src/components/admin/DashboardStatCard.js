import React from "react";
import {
  View,
  Text,
  StyleSheet,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

import THEME from "../../constants/theme";

export default function DashboardStatCard({
  title,
  value,
  subtitle,
  icon,
  iconColor,
  iconBackground,
  trend,
}) {
  return (
    <View style={styles.card}>
      {/* Top */}

      <View style={styles.topRow}>
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

        {trend && (
          <View style={styles.trendBadge}>
            <Ionicons
              name="trending-up"
              size={12}
              color={THEME.colors.success}
            />

            <Text style={styles.trendText}>
              {trend}
            </Text>
          </View>
        )}
      </View>

      {/* Number */}

      <Text style={styles.value}>
        {value}
      </Text>

      {/* Title */}

      <Text style={styles.title}>
        {title}
      </Text>

      {/* Subtitle */}

      {subtitle ? (
        <Text style={styles.subtitle}>
          {subtitle}
        </Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    width: "48%",

    backgroundColor:
      THEME.colors.card,

    borderRadius:
      THEME.radius.card,

    padding:
      THEME.spacing.cardPadding,

    borderWidth: 1,

    borderColor:
      THEME.colors.border,

    marginBottom:
      THEME.spacing.cardGap,

    ...THEME.shadows.md,
  },

  topRow: {
    flexDirection: "row",

    justifyContent:
      "space-between",

    alignItems: "center",

    marginBottom: 18,
  },

  iconContainer: {
    width: 52,

    height: 52,

    borderRadius: 14,

    justifyContent: "center",

    alignItems: "center",
  },

  trendBadge: {
    flexDirection: "row",

    alignItems: "center",

    backgroundColor:
      THEME.colors.greenBg,

    paddingHorizontal: 8,

    paddingVertical: 4,

    borderRadius: 20,
  },

  trendText: {
    marginLeft: 4,

    fontSize: 11,

    fontWeight: "700",

    color:
      THEME.colors.success,
  },

  value: {
    ...THEME.typography.statNumber,

    color: THEME.colors.text,
  },

  title: {
    marginTop: 4,

    ...THEME.typography.cardTitle,

    color:
      THEME.colors.textSecondary,
  },

  subtitle: {
    marginTop: 6,

    ...THEME.typography.caption,

    color:
      THEME.colors.textLight,
  },
});