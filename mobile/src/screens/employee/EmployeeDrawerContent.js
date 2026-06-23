import React from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  SafeAreaView,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { DrawerContentScrollView } from "@react-navigation/drawer";

import { employeeLogout } from "../../api/client";
import { useAuth } from "../../store/AuthContext";

export default function EmployeeDrawerContent(props) {
  const { navigation, state } = props;
  const { signOut } = useAuth();

  const activeRoute = state.routeNames[state.index];

  const handleLogout = async () => {
    try {
      await employeeLogout();
    } catch (e) {}

    signOut();
  };

  const menuItems = [
    {
      title: "Dashboard",
      icon: "grid-outline",
      route: "Home",
      section: "MAIN",
    },
    {
      title: "Attendance",
      icon: "time-outline",
      route: "Attendance",
      section: "MAIN",
    },
    {
      title: "Leave",
      icon: "calendar-outline",
      route: "Leave",
      section: "MAIN",
    },
    {
      title: "Payslips",
      icon: "wallet-outline",
      route: "Payslips",
      section: "MAIN",
    },
    {
      title: "Tickets",
      icon: "chatbubble-ellipses-outline",
      route: "Tickets",
      section: "WORK",
    },
    {
      title: "Announcements",
      icon: "megaphone-outline",
      route: "Announcements",
      section: "WORK",
    },
    {
      title: "Holidays",
      icon: "gift-outline",
      route: "Holidays",
      section: "WORK",
    },
    {
      title: "My Profile",
      icon: "person-circle-outline",
      route: "Profile",
      section: "ACCOUNT",
    },
    {
      title: "Settings",
      icon: "settings-outline",
      route: "Settings",
      section: "ACCOUNT",
    },
  ];

  const renderMenuItem = (item) => {
    const active = activeRoute === item.route;

    return (
      <TouchableOpacity
        key={item.title}
        activeOpacity={0.8}
        style={[
          styles.menuItem,
          active && styles.activeMenuItem,
        ]}
        onPress={() => {
          /**
           * Navigation will be connected
           * after all screens are created.
           */
          if (
            state.routeNames.includes(item.route)
          ) {
            navigation.navigate(item.route);
          }
        }}
      >
        <Ionicons
          name={item.icon}
          size={22}
          color={
            active
              ? "#FFFFFF"
              : "#173B8C"
          }
        />

        <Text
          style={[
            styles.menuText,
            active &&
              styles.activeMenuText,
          ]}
        >
          {item.title}
        </Text>

        <Ionicons
          name="chevron-forward"
          size={18}
          color={
            active
              ? "#FFFFFF"
              : "#94A3B8"
          }
        />
      </TouchableOpacity>
    );
  };

  const renderSection = (
    title,
    section
  ) => (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>
        {title}
      </Text>

      {menuItems
        .filter(
          (item) =>
            item.section === section
        )
        .map(renderMenuItem)}
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      <DrawerContentScrollView
        {...props}
        showsVerticalScrollIndicator={false}
        contentContainerStyle={
          styles.scrollContent
        }
      >
        {/* Profile Header */}

        <View style={styles.header}>
          <View style={styles.avatar}>
            <Ionicons
              name="person"
              size={42}
              color="#173B8C"
            />

            <View
              style={styles.onlineDot}
            />
          </View>

          <Text style={styles.name}>
            Employee
          </Text>

          <View
            style={styles.roleBadge}
          >
            <Text
              style={styles.roleText}
            >
              Software Engineer
            </Text>
          </View>

          <Text style={styles.empId}>
            EMP001
          </Text>
        </View>

        <View style={styles.divider} />

        {renderSection(
          "MAIN",
          "MAIN"
        )}

        {renderSection(
          "WORK",
          "WORK"
        )}

        {renderSection(
          "ACCOUNT",
          "ACCOUNT"
        )}

        <View style={styles.divider} />

        <TouchableOpacity
          style={styles.logoutButton}
          onPress={handleLogout}
        >
          <Ionicons
            name="log-out-outline"
            size={22}
            color="#EF4444"
          />

          <Text
            style={styles.logoutText}
          >
            Logout
          </Text>
        </TouchableOpacity>

        <Text style={styles.version}>
          Version 1.0.0
        </Text>
      </DrawerContentScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F7F9FC",
  },

  scrollContent: {
    paddingBottom: 30,
  },

  header: {
    alignItems: "center",
    paddingTop: 20,
    paddingBottom: 28,
    paddingHorizontal: 24,
    backgroundColor: "#FFFFFF",
  },

  avatar: {
    width: 90,
    height: 90,
    borderRadius: 45,
    backgroundColor: "#EEF4FF",
    justifyContent: "center",
    alignItems: "center",
    position: "relative",

    shadowColor: "#000",
    shadowOpacity: 0.08,
    shadowRadius: 10,
    shadowOffset: {
      width: 0,
      height: 5,
    },
    elevation: 4,
  },

  onlineDot: {
    position: "absolute",
    bottom: 8,
    right: 8,

    width: 16,
    height: 16,
    borderRadius: 8,

    backgroundColor: "#22C55E",

    borderWidth: 3,
    borderColor: "#FFFFFF",
  },

  name: {
    marginTop: 16,
    fontSize: 22,
    fontWeight: "800",
    color: "#0F172A",
  },

  roleBadge: {
    marginTop: 12,

    backgroundColor: "#EEF4FF",

    paddingHorizontal: 16,
    paddingVertical: 7,

    borderRadius: 30,
  },

  roleText: {
    color: "#173B8C",
    fontWeight: "700",
    fontSize: 13,
  },

  empId: {
    marginTop: 10,
    color: "#94A3B8",
    fontSize: 13,
    fontWeight: "600",
  },

  divider: {
    height: 1,
    backgroundColor: "#EEF2F7",
    marginVertical: 22,
    marginHorizontal: 20,
  },

  section: {
    marginBottom: 18,
    paddingHorizontal: 18,
  },

  sectionTitle: {
    marginBottom: 12,

    fontSize: 12,
    fontWeight: "700",

    color: "#94A3B8",

    letterSpacing: 1.2,

    marginLeft: 8,
  },

  menuItem: {
    height: 56,

    borderRadius: 18,

    paddingHorizontal: 18,

    marginBottom: 10,

    backgroundColor: "#FFFFFF",

    flexDirection: "row",

    alignItems: "center",

    shadowColor: "#000",
    shadowOpacity: 0.04,
    shadowRadius: 8,
    shadowOffset: {
      width: 0,
      height: 3,
    },

    elevation: 2,
  },

  activeMenuItem: {
    backgroundColor: "#173B8C",
  },

  menuText: {
    flex: 1,

    marginLeft: 14,

    color: "#0F172A",

    fontWeight: "700",

    fontSize: 15,
  },

  activeMenuText: {
    color: "#FFFFFF",
  },

  logoutButton: {
    marginHorizontal: 20,

    marginTop: 10,

    height: 56,

    borderRadius: 18,

    backgroundColor: "#FFF5F5",

    flexDirection: "row",

    alignItems: "center",

    justifyContent: "center",
  },

  logoutText: {
    marginLeft: 10,

    color: "#EF4444",

    fontWeight: "700",

    fontSize: 16,
  },

  version: {
    marginTop: 22,

    textAlign: "center",

    color: "#94A3B8",

    fontSize: 12,

    marginBottom: 20,
  },
});