import React from "react";
import { createDrawerNavigator } from "@react-navigation/drawer";
import ManagerDashboard from "../screens/roles/ManagerDashboard";
import ManagerDrawerContent from "../screens/roles/ManagerDrawerContent";
import AttendanceScreen from "../screens/admin/AttendanceScreen";
import LeaveRequestsScreen from "../screens/admin/LeaveRequestsScreen";
import EmployeesScreen from "../screens/admin/EmployeesScreen";
import CompOffScreen from "../screens/admin/CompOffScreen";
import PerformanceScreen from "../screens/admin/PerformanceScreen";
import MarkAttendanceScreen from "../screens/admin/MarkAttendanceScreen";
import AdminTicketsScreen from "../screens/admin/AdminTicketsScreen";
import SettingsScreen from "../screens/admin/SettingsScreen";

const Drawer = createDrawerNavigator();

export default function ManagerDrawerNavigator() {
  return (
    <Drawer.Navigator
      initialRouteName="ManagerDashboard"
      drawerContent={(props) => <ManagerDrawerContent {...props} />}
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
      <Drawer.Screen name="ManagerDashboard" component={ManagerDashboard} options={{ title: "Team Manager Hub" }} />
      <Drawer.Screen name="Attendance" component={AttendanceScreen} options={{ title: "Team Attendance" }} />
      <Drawer.Screen name="MarkAttendance" component={MarkAttendanceScreen} options={{ title: "Mark Team Attendance" }} />
      <Drawer.Screen name="LeaveRequests" component={LeaveRequestsScreen} options={{ title: "Team Approvals" }} />
      <Drawer.Screen name="Employees" component={EmployeesScreen} options={{ title: "Direct Reports" }} />
      <Drawer.Screen name="CompOff" component={CompOffScreen} options={{ title: "Comp-off Claims" }} />
      <Drawer.Screen name="Performance" component={PerformanceScreen} options={{ title: "Team KPIs" }} />
      <Drawer.Screen name="Tickets" component={AdminTicketsScreen} options={{ title: "Team Support Tickets" }} />
      <Drawer.Screen name="Settings" component={SettingsScreen} options={{ title: "Settings & Profile" }} />
    </Drawer.Navigator>
  );
}
