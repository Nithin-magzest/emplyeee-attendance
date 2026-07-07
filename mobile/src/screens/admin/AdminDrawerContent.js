import React from "react";

import {
  SafeAreaView,
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
} from "react-native";

import { DrawerContentScrollView } from "@react-navigation/drawer";

import { Ionicons } from "@expo/vector-icons";

import THEME from "../../constants/theme";

export default function AdminDrawerContent(props) {
  const { navigation, state } = props;

  const currentRoute =
    state.routeNames[state.index];

  const menuItems = [
    {
      title: "Dashboard",
      icon: "grid-outline",
      route: "Dashboard",
    },
    {
      title: "Employees",
      icon: "people-outline",
      route: "Employees",
    },
    {
      title: "Attendance",
      icon: "calendar-outline",
      route: "Attendance",
    },
    {
      title: "Leave Requests",
      icon: "document-text-outline",
      route: "LeaveRequests",
    },
    {
      title: "Payroll",
      icon: "wallet-outline",
      route: "Payroll",
    },
    {
      title: "Departments",
      icon: "business-outline",
      route: "Departments",
    },
    {
      title: "Analytics",
      icon: "bar-chart-outline",
      route: "Analytics",
    },
    {
      title: "Reports",
      icon: "stats-chart-outline",
      route: "Reports",
    },
    {
      title: "Settings",
      icon: "settings-outline",
      route: "Settings",
    },
  ];

  const renderItem = (item) => {
    const active =
      currentRoute === item.route;

    return (
      <TouchableOpacity
        key={item.route}
        activeOpacity={0.8}
        style={[
          styles.item,
          active && styles.activeItem,
        ]}
        onPress={() => {
          navigation.navigate(
            "AdminTabs",
            {
              screen: item.route,
            }
          );

          navigation.closeDrawer();
        }}
      >
        <Ionicons
          name={item.icon}
          size={22}
          color={
            active
              ? "#FFFFFF"
              : THEME.colors.primary
          }
        />

        <Text
          style={[
            styles.itemText,
            active &&
              styles.activeText,
          ]}
        >
          {item.title}
        </Text>
      </TouchableOpacity>
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <DrawerContentScrollView>

        {/* Header */}

        <View style={styles.header}>
          <View style={styles.avatar}>
            <Ionicons
              name="person"
              size={42}
              color={THEME.colors.primary}
            />
          </View>

          <Text style={styles.name}>
            Administrator
          </Text>

          <Text style={styles.role}>
            HR Management System
          </Text>
        </View>

        <View style={styles.divider} />

        {menuItems.map(renderItem)}

      </DrawerContentScrollView>

      <TouchableOpacity
        style={styles.logout}
      >
        <Ionicons
          name="log-out-outline"
          size={22}
          color="#EF4444"
        />

        <Text style={styles.logoutText}>
          Logout
        </Text>
      </TouchableOpacity>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor:
      THEME.colors.background,
  },

  header: {
    alignItems: "center",
    paddingVertical: 30,
  },

  avatar: {
    width: 80,
    height: 80,
    borderRadius: 40,

    backgroundColor:
      THEME.colors.blueBg,

    justifyContent: "center",
    alignItems: "center",
  },

  name: {
    marginTop: 18,

    ...THEME.typography.headerTitle,

    color: THEME.colors.text,
  },

  role: {
    marginTop: 6,

    ...THEME.typography.caption,

    color:
      THEME.colors.textSecondary,
  },

  divider: {
    height: 1,

    backgroundColor:
      THEME.colors.border,

    marginBottom: 16,
  },

  item: {
    flexDirection: "row",

    alignItems: "center",

    height: 52,

    marginHorizontal: 16,

    marginBottom: 8,

    borderRadius:
      THEME.radius.button,

    paddingHorizontal: 16,
  },

  activeItem: {
    backgroundColor:
      THEME.colors.primary,
  },

  itemText: {
    marginLeft: 16,

    ...THEME.typography.bodyMedium,

    color: THEME.colors.text,
  },

  activeText: {
    color: "#FFFFFF",
  },

  logout: {
    height: 60,

    flexDirection: "row",

    alignItems: "center",

    paddingHorizontal: 22,

    borderTopWidth: 1,

    borderTopColor:
      THEME.colors.border,
  },

  logoutText: {
    marginLeft: 14,

    color: "#EF4444",

    ...THEME.typography.bodyMedium,
  },
});