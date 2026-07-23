import React from "react";
import { createDrawerNavigator } from "@react-navigation/drawer";
import AttendanceScreen from "../screens/employee/AttendanceScreen";
import EmployeeNavigator from "./EmployeeNavigator";

import EmployeeDrawerContent from "../screens/employee/EmployeeDrawerContent";
import CompOffScreen from "../screens/employee/CompOffScreen";

const Drawer = createDrawerNavigator();

export default function EmployeeDrawerNavigator() {
  return (
    <Drawer.Navigator
      initialRouteName="EmployeeTabs"
      drawerContent={(props) => (
        <EmployeeDrawerContent {...props} />
      )}
      screenOptions={{
        headerShown: false,
        drawerType: "slide",
        drawerPosition: "left",
        swipeEnabled: true,

        overlayColor: "rgba(15,23,42,0.25)",

        drawerStyle: {
          width: 310,
          backgroundColor: "#F7F9FC",
          borderTopRightRadius: 28,
          borderBottomRightRadius: 28,
        },

        sceneContainerStyle: {
          backgroundColor: "#F7F9FC",
        },
      }}
    >
      {/* Bottom Tab Navigator */}
      <Drawer.Screen
        name="EmployeeTabs"
        component={EmployeeNavigator}
      />

      {/* Future Screens */}

    
      
      <Drawer.Screen
  name="CompOff"
  component={CompOffScreen}
/>



{/*
      <Drawer.Screen
        name="Profile"
        component={ProfileScreen}
      />

      <Drawer.Screen
        name="Payslips"
        component={PayslipsScreen}
      />

      

      <Drawer.Screen
        name="Settings"
        component={SettingsScreen}
      />
      */}
    </Drawer.Navigator>);
}