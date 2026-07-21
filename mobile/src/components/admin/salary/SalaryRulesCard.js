import React, { useState } from "react";

import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

import SALARY_THEME from "../../../constants/salaryTheme";

const getRuleColor = (type) => {
  switch (type) {
    case "success":
      return {
        icon: "checkmark-circle",
        color: SALARY_THEME.colors.success,
        background:
          SALARY_THEME.colors.successLight,
      };

    case "warning":
      return {
        icon: "warning",
        color: SALARY_THEME.colors.warning,
        background:
          SALARY_THEME.colors.warningLight,
      };

    case "danger":
      return {
        icon: "close-circle",
        color: SALARY_THEME.colors.danger,
        background:
          SALARY_THEME.colors.dangerLight,
      };

    case "approved":
      return {
        icon: "calendar",
        color: SALARY_THEME.colors.primary,
        background:
          SALARY_THEME.colors.primaryLight,
      };

    default:
      return {
        icon: "information-circle",
        color: SALARY_THEME.colors.purple,
        background:
          SALARY_THEME.colors.purpleLight,
      };
  }
};

export default function SalaryRulesCard({
  rules,
}) {
  const [expanded, setExpanded] =
    useState(false);

  return (
    <View style={styles.card}>

      <TouchableOpacity
        activeOpacity={0.85}
        style={styles.header}
        onPress={() =>
          setExpanded(!expanded)
        }
      >

        <View style={styles.headerLeft}>

          <View style={styles.headerIcon}>

            <Ionicons
              name="shield-checkmark"
              size={22}
              color={
                SALARY_THEME.colors.primary
              }
            />

          </View>

          <View>

            <Text style={styles.title}>
              Payroll Rules
            </Text>

            <Text style={styles.subtitle}>
              Salary calculation policy
            </Text>

          </View>

        </View>

        <Ionicons
          name={
            expanded
              ? "chevron-up"
              : "chevron-down"
          }
          size={22}
          color={
            SALARY_THEME.colors.textMuted
          }
        />

      </TouchableOpacity>

      {expanded && (

        <View style={styles.rulesContainer}>

          {rules.map((rule) => {

            const status =
              getRuleColor(rule.type);

            return (

              <View
                key={rule.id}
                style={styles.ruleItem}
              >

                <View
                  style={[
                    styles.ruleIcon,
                    {
                      backgroundColor:
                        status.background,
                    },
                  ]}
                >

                  <Ionicons
                    name={status.icon}
                    size={20}
                    color={status.color}
                  />

                </View>

                <View
                  style={styles.ruleContent}
                >

                  <Text
                    style={styles.ruleTitle}
                  >
                    {rule.title}
                  </Text>

                  <Text
                    style={
                      styles.ruleDescription
                    }
                  >
                    {rule.description}
                  </Text>

                </View>

              </View>

            );
          })}

        </View>

      )}

    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor:
      SALARY_THEME.colors.surface,

    borderRadius:
      SALARY_THEME.radius.lg,

    borderWidth: 1,

    borderColor:
      SALARY_THEME.colors.border,

    marginBottom: 20,

    overflow: "hidden",

    ...SALARY_THEME.shadow,
  },

  header: {
    padding: 18,

    flexDirection: "row",

    justifyContent: "space-between",

    alignItems: "center",
  },

  headerLeft: {
    flexDirection: "row",

    alignItems: "center",

    flex: 1,
  },

  headerIcon: {
    width: 48,

    height: 48,

    borderRadius: 14,

    backgroundColor:
      SALARY_THEME.colors.primaryLight,

    justifyContent: "center",

    alignItems: "center",

    marginRight: 14,
  },

  title: {
    fontSize: 17,

    fontWeight: "700",

    color:
      SALARY_THEME.colors.textPrimary,
  },

  subtitle: {
    marginTop: 4,

    fontSize: 13,

    color:
      SALARY_THEME.colors.textMuted,
  },

  rulesContainer: {
    paddingHorizontal: 18,

    paddingBottom: 18,
  },

  ruleItem: {
    flexDirection: "row",

    alignItems: "flex-start",

    marginTop: 18,
  },

  ruleIcon: {
    width: 42,

    height: 42,

    borderRadius: 12,

    justifyContent: "center",

    alignItems: "center",

    marginRight: 14,
  },

  ruleContent: {
    flex: 1,
  },

  ruleTitle: {
    fontSize: 15,

    fontWeight: "700",

    color:
      SALARY_THEME.colors.textPrimary,
  },

  ruleDescription: {
    marginTop: 5,

    fontSize: 13,

    lineHeight: 20,

    color:
      SALARY_THEME.colors.textMuted,
  },
});