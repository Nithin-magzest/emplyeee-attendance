import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Ionicons } from '@expo/vector-icons';
import EmployeeDashboard from '../screens/employee/EmployeeDashboard';
import LeaveScreen       from '../screens/employee/LeaveScreen';
import ResignScreen      from '../screens/employee/ResignScreen';
import TicketsScreen     from '../screens/employee/TicketsScreen';
import NotificationsScreen from '../screens/NotificationsScreen';
import { COLORS } from '../config';

const Tab = createBottomTabNavigator();

export default function EmployeeNavigator() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarStyle: {
          backgroundColor: '#0f3460',
          borderTopColor: 'rgba(255,255,255,0.10)',
          height: 62,
          paddingBottom: 8,
        },
        tabBarActiveTintColor:   '#fff',
        tabBarInactiveTintColor: 'rgba(255,255,255,0.45)',
        tabBarIcon: ({ focused, size }) => {
          const map = {
            Home:          focused ? 'home'              : 'home-outline',
            Leave:         focused ? 'document-text'     : 'document-text-outline',
            Tickets:       focused ? 'ticket'            : 'ticket-outline',
            Resign:        focused ? 'exit'              : 'exit-outline',
            Notifications: focused ? 'notifications'     : 'notifications-outline',
          };
          const colors = {
            Home:          focused ? '#6ee56e' : 'rgba(255,255,255,0.45)',
            Leave:         focused ? '#93c5fd' : 'rgba(255,255,255,0.45)',
            Tickets:       focused ? '#a5b4fc' : 'rgba(255,255,255,0.45)',
            Resign:        focused ? '#fca5a5' : 'rgba(255,255,255,0.45)',
            Notifications: focused ? '#fbbf24' : 'rgba(255,255,255,0.45)',
          };
          return <Ionicons name={map[route.name]} size={size} color={colors[route.name]} />;
        },
        tabBarActiveTintColor: undefined,
      })}
    >
      <Tab.Screen name="Home"          component={EmployeeDashboard}   options={{ tabBarLabel: '🏠 Home',    tabBarActiveTintColor: '#6ee56e' }} />
      <Tab.Screen name="Leave"         component={LeaveScreen}         options={{ tabBarLabel: '📋 Leave',   tabBarActiveTintColor: '#93c5fd' }} />
      <Tab.Screen name="Tickets"       component={TicketsScreen}       options={{ tabBarLabel: '🎫 Tickets', tabBarActiveTintColor: '#a5b4fc' }} />
      <Tab.Screen name="Resign"        component={ResignScreen}        options={{ tabBarLabel: '🚨 Resign',  tabBarActiveTintColor: '#fca5a5' }} />
      <Tab.Screen name="Notifications" component={NotificationsScreen} options={{ tabBarLabel: '🔔 Alerts',  tabBarActiveTintColor: '#fbbf24' }} />
    </Tab.Navigator>
  );
}
