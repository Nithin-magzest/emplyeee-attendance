import React from 'react';
import { View, ActivityIndicator } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { StatusBar } from 'expo-status-bar';
import { GestureHandlerRootView } from 'react-native-gesture-handler';

import { AuthProvider, useAuth } from './src/store/AuthContext';
import LoginScreen      from './src/screens/LoginScreen';
import AdminNavigator   from './src/navigation/AdminNavigator';
import EmployeeDrawerNavigator from './src/navigation/EmployeeDrawerNavigator';

function RootNavigator() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <View
        style={{
          flex: 1,
          backgroundColor: "#0f2027",
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        <ActivityIndicator size="large" color="#fff" />
      </View>
    );
  }

  if (!user) return <LoginScreen />;

  if (user.role === "admin") {
    return <AdminNavigator />;
  }

  if (user.role === "employee") {
    return <EmployeeDrawerNavigator />;
  }

  return <LoginScreen />;
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
