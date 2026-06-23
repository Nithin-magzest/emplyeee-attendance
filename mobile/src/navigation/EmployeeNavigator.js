import React from "react";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { Ionicons } from "@expo/vector-icons";

import EmployeeDashboard from "../screens/employee/EmployeeDashboard";
import LeaveScreen from "../screens/employee/LeaveScreen";
import TicketsScreen from "../screens/employee/TicketsScreen";
import NotificationsScreen from "../screens/NotificationsScreen";

// Replace this with your actual QR screen
import AttendanceScreen from "../screens/employee/AttendanceScreen";

const Tab = createBottomTabNavigator();

export default function EmployeeNavigator() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,

        tabBarHideOnKeyboard: true,

      tabBarStyle: {
  position: "absolute",

  left: 24,
  right: 24,
  bottom: 24,

  height: 78,

  borderRadius: 28,

  backgroundColor: "#173B8C",

  borderTopWidth: 0,

  elevation: 25,

  shadowColor: "#000",
  shadowOpacity: 0.18,
  shadowRadius: 24,
  shadowOffset: {
    width: 0,
    height: 12,
  },

  paddingBottom: 10,
  paddingTop: 10,
},

       tabBarLabelStyle: {
  fontSize: 10,
  fontWeight: "700",
  marginTop: 3,
},

        tabBarActiveTintColor: "#FFFFFF",
        tabBarInactiveTintColor: "rgba(255,255,255,0.55)",

        tabBarIcon: ({ focused, color, size }) => {
          if (route.name === "Home") {
            return (
              <Ionicons
                name={focused ? "home" : "home-outline"}
                size={22}
                color={color}
              />
            );
          }

          if (route.name === "Leave") {
            return (
              <Ionicons
                name={focused ? "document-text" : "document-text-outline"}
                size={24}
                color={color}
              />
            );
          }

          if (route.name === "Scan") {
            return (
              <Ionicons
                name="qr-code"
                size={30}
                color="#FFFFFF"
              />
            );
          }

          if (route.name === "Tickets") {
            return (
              <Ionicons
                name={focused ? "ticket" : "ticket-outline"}
                size={24}
                color={color}
              />
            );
          }

          return (
            <Ionicons
              name={
                focused
                  ? "notifications"
                  : "notifications-outline"
              }
              size={24}
              color={color}
            />
          );
        },
      })}
    >
      <Tab.Screen
        name="Home"
        component={EmployeeDashboard}
        options={{
          tabBarLabel: "Home",
        }}
      />

      <Tab.Screen
        name="Leave"
        component={LeaveScreen}
        options={{
          tabBarLabel: "Leave",
        }}
      />

      <Tab.Screen
        name="Scan"
        component={AttendanceScreen}
        options={{
          tabBarLabel: "Scan",

          tabBarItemStyle: {
            top: -18,
          },

          tabBarIcon: () => (
            <View
  style={{
    width: 66,
    height: 66,
    borderRadius: 33,

    backgroundColor: "#22C55E",

    justifyContent: "center",
    alignItems: "center",

    borderWidth: 5,
    borderColor: "#FFFFFF",

    shadowColor: "#22C55E",
    shadowOpacity: 0.45,
    shadowRadius: 18,
    shadowOffset: {
      width: 0,
      height: 8,
    },
    elevation: 16,
  }}
>
  <Ionicons
      name="qr-code"
      size={30}
      color="#FFFFFF"
  />
</View>
          ),

          tabBarIconStyle: {
            backgroundColor: "#22C55E",
            width: 64,
            height: 64,
            borderRadius: 32,

            justifyContent: "center",
            alignItems: "center",

            shadowColor: "#22C55E",
            shadowOpacity: 0.35,
            shadowRadius: 12,
            shadowOffset: {
              width: 0,
              height: 6,
            },
            elevation: 10,
          },
        }}
      />

      <Tab.Screen
        name="Tickets"
        component={TicketsScreen}
        options={{
          tabBarLabel: "Tickets",
        }}
      />

      <Tab.Screen
        name="Notifications"
        component={NotificationsScreen}
        options={{
          tabBarLabel: "Alerts",
        }}
      />
    </Tab.Navigator>
  );
}