import React, { useState } from "react";
import { View, ActivityIndicator } from "react-native";
import { NavigationContainer } from "@react-navigation/native";
import { StatusBar } from "expo-status-bar";
import { GestureHandlerRootView } from "react-native-gesture-handler";

import { AuthProvider, useAuth } from "./src/store/AuthContext";
import LaunchCountdownScreen from "./src/screens/LaunchCountdownScreen";
import LoginScreen from "./src/screens/LoginScreen";
import AdminDrawerNavigator from "./src/navigation/AdminDrawerNavigator";
import EmployeeDrawerNavigator from "./src/navigation/EmployeeDrawerNavigator";
import SuperAdminDrawerNavigator from "./src/navigation/SuperAdminDrawerNavigator";
import HrDrawerNavigator from "./src/navigation/HrDrawerNavigator";
import ManagerDrawerNavigator from "./src/navigation/ManagerDrawerNavigator";
import SecOpsDrawerNavigator from "./src/navigation/SecOpsDrawerNavigator";

function RootNavigator() {
  const { user, loading } = useAuth();
  const [showLaunch, setShowLaunch] = useState(true);

  if (loading) {
    return (
      <View
        style={{
          flex: 1,
          backgroundColor: "#0F172A",
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        <ActivityIndicator size="large" color="#FFFFFF" />
      </View>
    );
  }

  if (!user) {
    if (showLaunch) {
      return (
        <LaunchCountdownScreen
          onContinue={() => setShowLaunch(false)}
        />
      );
    }
    return <LoginScreen />;
  }

  // Enterprise HRMS SaaS Role-Based Navigation
  const role = (user.role || "employee").toLowerCase();

  if (role === "superadmin" || role === "platform_admin") {
    return <SuperAdminDrawerNavigator />;
  }

  if (role === "admin") {
    return <AdminDrawerNavigator />;
  }

  if (role === "hr" || role === "hr_manager") {
    return <HrDrawerNavigator />;
  }

  if (role === "manager" || role === "team_lead") {
    return <ManagerDrawerNavigator />;
  }

  if (role === "soc_analyst" || role === "secops" || role === "cybersecurity") {
    return <SecOpsDrawerNavigator />;
  }

  if (role === "employee") {
    return <EmployeeDrawerNavigator />;
  }

  return <EmployeeDrawerNavigator />;
}

export default function App() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <AuthProvider>
        <NavigationContainer>
          <StatusBar style="light" />
          <RootNavigator />
        </NavigationContainer>
      </AuthProvider>
    </GestureHandlerRootView>
  );
}
