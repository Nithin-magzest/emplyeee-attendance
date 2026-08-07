import React from "react";
import { createDrawerNavigator } from "@react-navigation/drawer";
import SuperAdminDashboard from "../screens/roles/SuperAdminDashboard";
import SuperAdminDrawerContent from "../screens/roles/SuperAdminDrawerContent";
import SettingsScreen from "../screens/admin/SettingsScreen";
import AnalyticsScreen from "../screens/admin/AnalyticsScreen";
import OrgChartScreen from "../screens/admin/OrgChartScreen";

const Drawer = createDrawerNavigator();

export default function SuperAdminDrawerNavigator() {
  return (
    <Drawer.Navigator
      initialRouteName="SuperAdminDashboard"
      drawerContent={(props) => <SuperAdminDrawerContent {...props} />}
      screenOptions={{
        headerShown: false,
        drawerType: "slide",
        drawerPosition: "left",
        overlayColor: "rgba(15, 23, 42, 0.6)",
        drawerStyle: {
          width: 310,
          backgroundColor: "#0F172A",
        },
        sceneContainerStyle: {
          backgroundColor: "#0F172A",
        },
      }}
    >
      <Drawer.Screen name="SuperAdminDashboard" component={SuperAdminDashboard} options={{ title: "SaaS Dashboard" }} />
      <Drawer.Screen name="Analytics" component={AnalyticsScreen} options={{ title: "Global Analytics" }} />
      <Drawer.Screen name="OrgChart" component={OrgChartScreen} options={{ title: "Tenant Hierarchies" }} />
      <Drawer.Screen name="Settings" component={SettingsScreen} options={{ title: "System Configuration" }} />
    </Drawer.Navigator>
  );
}
