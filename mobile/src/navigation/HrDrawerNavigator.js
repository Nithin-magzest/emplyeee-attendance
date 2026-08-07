import React from "react";
import { createDrawerNavigator } from "@react-navigation/drawer";
import HrDashboard from "../screens/roles/HrDashboard";
import HrDrawerContent from "../screens/roles/HrDrawerContent";
import EmployeesScreen from "../screens/admin/EmployeesScreen";
import LeaveRequestsScreen from "../screens/admin/LeaveRequestsScreen";
import OnboardingScreen from "../screens/admin/OnboardingScreen";
import PerformanceScreen from "../screens/admin/PerformanceScreen";
import AdminTicketsScreen from "../screens/admin/AdminTicketsScreen";
import ResignationsScreen from "../screens/admin/ResignationsScreen";
import OrgChartScreen from "../screens/admin/OrgChartScreen";
import LeavesHolidaysScreen from "../screens/admin/LeavesHolidaysScreen";
import DepartmentsScreen from "../screens/admin/DepartmentsScreen";
import SettingsScreen from "../screens/admin/SettingsScreen";

const Drawer = createDrawerNavigator();

export default function HrDrawerNavigator() {
  return (
    <Drawer.Navigator
      initialRouteName="HrDashboard"
      drawerContent={(props) => <HrDrawerContent {...props} />}
      screenOptions={{
        headerShown: false,
        drawerType: "slide",
        drawerPosition: "left",
        overlayColor: "rgba(15, 23, 42, 0.4)",
        drawerStyle: {
          width: 310,
          backgroundColor: "#F8FAFC",
        },
        sceneContainerStyle: {
          backgroundColor: "#F8FAFC",
        },
      }}
    >
      <Drawer.Screen name="HrDashboard" component={HrDashboard} options={{ title: "HR Dashboard" }} />
      <Drawer.Screen name="Employees" component={EmployeesScreen} options={{ title: "Employee Master" }} />
      <Drawer.Screen name="LeaveRequests" component={LeaveRequestsScreen} options={{ title: "Leave Approvals" }} />
      <Drawer.Screen name="Onboarding" component={OnboardingScreen} options={{ title: "Onboarding Pipeline" }} />
      <Drawer.Screen name="Performance" component={PerformanceScreen} options={{ title: "Performance Reviews" }} />
      <Drawer.Screen name="Tickets" component={AdminTicketsScreen} options={{ title: "HR Helpdesk Tickets" }} />
      <Drawer.Screen name="Resignations" component={ResignationsScreen} options={{ title: "Offboarding & Resignations" }} />
      <Drawer.Screen name="OrgChart" component={OrgChartScreen} options={{ title: "Org Hierarchy" }} />
      <Drawer.Screen name="LeavesHolidays" component={LeavesHolidaysScreen} options={{ title: "Leaves & Holidays" }} />
      <Drawer.Screen name="Departments" component={DepartmentsScreen} options={{ title: "Departments & Units" }} />
      <Drawer.Screen name="Settings" component={SettingsScreen} options={{ title: "Settings & Profile" }} />
    </Drawer.Navigator>
  );
}
