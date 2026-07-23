import React from "react";

import {
  View,
  Text,
 StyleSheet,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

import SALARY_THEME from "../../../constants/salaryTheme";

export default function PayrollStatusChip({
  status = "Pending",
}) {
  const getStatus = () => {
    switch (status) {
      case "Completed":
        return {
          icon: "checkmark-circle",
          background:
            SALARY_THEME.colors.successLight,
          color:
            SALARY_THEME.colors.success,
        };

      case "Processing":
        return {
          icon: "time",
          background:
            SALARY_THEME.colors.primaryLight,
          color:
            SALARY_THEME.colors.primary,
        };

      case "Draft":
        return {
          icon: "create",
          background:
            SALARY_THEME.colors.warningLight,
          color:
            SALARY_THEME.colors.warning,
        };

      case "Locked":
        return {
          icon: "lock-closed",
          background:
            SALARY_THEME.colors.dangerLight,
          color:
            SALARY_THEME.colors.danger,
        };

      case "Pending":
      default:
        return {
          icon: "alert-circle",
          background:
            SALARY_THEME.colors.warningLight,
          color:
            SALARY_THEME.colors.warning,
        };
    }
  };

  const chip = getStatus();

  return (
    <View
      style={[
        styles.container,
        {
          backgroundColor:
            chip.background,
        },
      ]}
    >
      <Ionicons
        name={chip.icon}
        size={14}
        color={chip.color}
      />

      <Text
        style={[
          styles.text,
          {
            color: chip.color,
          },
        ]}
      >
        {status}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",

    alignItems: "center",

    alignSelf: "flex-start",

    paddingHorizontal: 12,

    paddingVertical: 6,

    borderRadius: 20,
  },

  text: {
    marginLeft: 6,

    fontSize: 12,

    fontWeight: "700",
  },
});