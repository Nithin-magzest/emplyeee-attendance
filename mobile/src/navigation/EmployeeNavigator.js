import React from "react";
import { View } from "react-native";
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
  left: 0,
  right: 0,
  bottom: 0,
  height: 72,
  backgroundColor: "#173B8C",
  borderTopWidth: 0,
  borderTopLeftRadius: 26,
  borderTopRightRadius: 26,
  elevation: 15,
  shadowColor: "#000",
  shadowOpacity: 0.12,
  shadowRadius: 20,
  shadowOffset: {
    width: 0,
    height: -3,
  },
  paddingTop: 8,
  paddingBottom: 8,
},
tabBarLabelStyle: {
  fontSize: 11,
  fontWeight: "600",
  marginTop: -2,
},

tabBarLabelStyle: {
  fontSize: 10,
  fontWeight: "600",
  marginTop: 2,
},

        tabBarActiveTintColor: "#FFFFFF",
        tabBarInactiveTintColor: "rgba(255,255,255,0.72)",

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
                size={22}
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
                size={22}
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
              size={22}
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
          tabBarLabel: "",

          tabBarItemStyle: {
            top: 3,
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

    borderWidth: 3,
    borderColor: "#FFFFFF",

    shadowColor: "#22C55E",
    shadowOpacity: 0.45,
    shadowRadius: 18,
    shadowOffset: {
      width: 0,
      height: 8,
    },
    elevation: 18,
  }}
>
  <Ionicons
    name="qr-code"
    size={30}
    color="#FFFFFF"
  />
</View>
         ),

          
          tabBarStyle: {
  position: "absolute",

  left: 0,
  right: 0,
  bottom: 0,

  height: 72,

  backgroundColor: "#173B8C",

  borderTopWidth: 0,

  borderTopLeftRadius: 26,
  borderTopRightRadius: 26,

  elevation: 15,

  shadowColor: "#000",
  shadowOpacity: 0.12,
  shadowRadius: 20,
  shadowOffset: {
    width: 0,
    height: -3,
  },

  paddingTop: 8,
  paddingBottom: 8,
},
tabBarLabelStyle: {
  fontSize: 11,
  fontWeight: "600",
  marginTop: -2,
}
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