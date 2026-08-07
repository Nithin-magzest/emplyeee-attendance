import React from "react";
import { createDrawerNavigator } from "@react-navigation/drawer";
import SecOpsDashboard from "../screens/roles/SecOpsDashboard";
import SecOpsDrawerContent from "../screens/roles/SecOpsDrawerContent";
import AnalyticsScreen from "../screens/admin/AnalyticsScreen";
import SettingsScreen from "../screens/admin/SettingsScreen";
import SecurityScreen from "../screens/employee/SecurityScreen";
import AdminTicketsScreen from "../screens/admin/AdminTicketsScreen";

const Drawer = createDrawerNavigator();

export default function SecOpsDrawerNavigator() {
  return (
    <Drawer.Navigator
      initialRouteName="SecOpsDashboard"
      drawerContent={(props) => <SecOpsDrawerContent {...props} />}
      screenOptions={{
        headerShown: false,
        drawerType: "slide",
        drawerPosition: "left",
        overlayColor: "rgba(15, 23, 42, 0.7)",
        drawerStyle: {
          width: 300,
          backgroundColor: "#090D16",
        },
        sceneContainerStyle: {
          backgroundColor: "#090D16",
        },
      }}
    >
      <Drawer.Screen name="SecOpsDashboard" component={SecOpsDashboard} options={{ title: "SIEM Command Center" }} />
      <Drawer.Screen name="Analytics" component={AnalyticsScreen} options={{ title: "Security Telemetry" }} />
      <Drawer.Screen name="Security" component={SecurityScreen} options={{ title: "Audit & Risk Audit" }} />
      <Drawer.Screen name="Tickets" component={AdminTicketsScreen} options={{ title: "Security Incident Tickets" }} />
      <Drawer.Screen name="Settings" component={SettingsScreen} options={{ title: "Security Controls" }} />
    </Drawer.Navigator>
  );
}
