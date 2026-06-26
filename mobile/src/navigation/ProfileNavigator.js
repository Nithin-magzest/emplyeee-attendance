import React from "react";
import { createStackNavigator } from "@react-navigation/stack";

import ProfileScreen from "../screens/employee/ProfileScreen";
import PersonalInfoScreen from "../screens/employee/PersonalInfoScreen";
import WorkInfoScreen from "../screens/employee/WorkInfoScreen";

const Stack = createStackNavigator();

export default function ProfileNavigator() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen
        name="ProfileHome"
        component={ProfileScreen}
      />

      <Stack.Screen
        name="PersonalInfo"
        component={PersonalInfoScreen}
      />
       <Stack.Screen
        name="WorkInfo"
        component={WorkInfoScreen}
      />
    </Stack.Navigator>
  );
}