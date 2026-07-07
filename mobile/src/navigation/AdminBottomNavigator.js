import React from "react";

import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";

import { Ionicons } from "@expo/vector-icons";

import AdminDashboard from "../screens/admin/AdminDashboard";

// These screens will be created next
import EmployeesScreen from "../screens/admin/EmployeesScreen";
import AttendanceScreen from "../screens/admin/AttendanceScreen";
import AnalyticsScreen from "../screens/admin/AnalyticsScreen";
import SettingsScreen from "../screens/admin/SettingsScreen";

import THEME from "../constants/theme";

const Tab = createBottomTabNavigator();

export default function AdminBottomNavigator() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,

        tabBarHideOnKeyboard: true,

        tabBarActiveTintColor:
          THEME.colors.primary,

        tabBarInactiveTintColor:
          THEME.colors.textLight,

        tabBarStyle: {
          height: 72,

          backgroundColor:
            THEME.colors.surface,

          borderTopWidth: 1,

          borderTopColor:
            THEME.colors.border,

          paddingTop: 8,

          paddingBottom: 8,
        },

        tabBarLabelStyle: {
          ...THEME.typography.navLabel,
        },

        tabBarIcon: ({
          focused,
          color,
        }) => {
          let icon = "ellipse";

          switch (route.name) {
            case "Dashboard":
              icon = focused
                ? "grid"
                : "grid-outline";
              break;

            case "Employees":
              icon = focused
                ? "people"
                : "people-outline";
              break;

            case "Attendance":
              icon = focused
                ? "calendar"
                : "calendar-outline";
              break;

            case "Analytics":
              icon = focused
                ? "bar-chart"
                : "bar-chart-outline";
              break;

            case "Settings":
              icon = focused
                ? "settings"
                : "settings-outline";
              break;
          }

          return (
            <Ionicons
              name={icon}
              size={22}
              color={color}
            />
          );
        },
      })}
    >
      <Tab.Screen
        name="Dashboard"
        component={AdminDashboard}
      />

      <Tab.Screen
        name="Employees"
        component={EmployeesScreen}
      />

      <Tab.Screen
        name="Attendance"
        component={AttendanceScreen}
      />

      <Tab.Screen
        name="Analytics"
        component={AnalyticsScreen}
      />

      <Tab.Screen
        name="Settings"
        component={SettingsScreen}
      />
    </Tab.Navigator>
  );
}