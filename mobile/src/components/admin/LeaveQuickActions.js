import React from "react";

import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

import LEAVE_THEME from "../../constants/leaveTheme";

const ACTIONS = [
  {
    id: 1,
    title: "Apply",
    icon: "add-circle-outline",
    color: LEAVE_THEME.colors.primary,
    bg: LEAVE_THEME.colors.primaryLight,
  },
  {
    id: 2,
    title: "Calendar",
    icon: "calendar-outline",
    color: LEAVE_THEME.colors.success,
    bg: LEAVE_THEME.colors.successLight,
  },
  {
    id: 3,
    title: "Reports",
    icon: "bar-chart-outline",
    color: LEAVE_THEME.colors.purple,
    bg: LEAVE_THEME.colors.purpleLight,
  },
  {
    id: 4,
    title: "Balance",
    icon: "pie-chart-outline",
    color: LEAVE_THEME.colors.warning,
    bg: LEAVE_THEME.colors.warningLight,
  },
];

export default function LeaveQuickActions({
  onApply,
  onCalendar,
  onReports,
  onBalance,
}) {

  const handlePress = (title) => {

    switch (title) {

      case "Apply":
        onApply && onApply();
        break;

      case "Calendar":
        onCalendar && onCalendar();
        break;

      case "Reports":
        onReports && onReports();
        break;

      case "Balance":
        onBalance && onBalance();
        break;

      default:
        break;

    }

  };

  return (

    <View style={styles.container}>

      <Text style={styles.heading}>
        Quick Actions
      </Text>

      <View style={styles.grid}>

        {ACTIONS.map((item) => (

          <TouchableOpacity
            key={item.id}
            activeOpacity={0.85}
            style={styles.card}
            onPress={() =>
              handlePress(item.title)
            }
          >

            <View
              style={[
                styles.iconContainer,
                {
                  backgroundColor: item.bg,
                },
              ]}
            >

              <Ionicons
                name={item.icon}
                size={26}
                color={item.color}
              />

            </View>

            <Text style={styles.title}>
              {item.title}
            </Text>

          </TouchableOpacity>

        ))}

      </View>

    </View>

  );

}

const styles = StyleSheet.create({

  container: {
    marginBottom: 22,
  },

  heading: {
    fontSize: 18,

    fontWeight: "800",

    color:
      LEAVE_THEME.colors.textPrimary,

    marginBottom: 14,
  },

  grid: {
    flexDirection: "row",

    justifyContent: "space-between",

    flexWrap: "wrap",
  },

  card: {
    width: "48%",

    backgroundColor: "#FFFFFF",

    borderRadius: 20,

    paddingVertical: 22,

    alignItems: "center",

    marginBottom: 14,

    borderWidth: 1,

    borderColor:
      LEAVE_THEME.colors.border,

    ...LEAVE_THEME.shadow,
  },

  iconContainer: {
    width: 60,

    height: 60,

    borderRadius: 18,

    justifyContent: "center",

    alignItems: "center",

    marginBottom: 14,
  },

  title: {
    fontSize: 15,

    fontWeight: "700",

    color:
      LEAVE_THEME.colors.textPrimary,
  },

});