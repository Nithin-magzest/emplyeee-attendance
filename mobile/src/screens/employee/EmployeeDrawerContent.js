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
import { getFocusedRouteNameFromRoute } from "@react-navigation/native";
import { employeeLogout } from "../../api/client";
import { useAuth } from "../../store/AuthContext";

export default function EmployeeDrawerContent(props) {
  const { navigation, state } = props;
  const { signOut } = useAuth();

  

const drawerRoute = state.routes[state.index];

const activeRoute =
  getFocusedRouteNameFromRoute(drawerRoute) ??
  drawerRoute.name;

  const handleLogout = async () => {
    try {
      await employeeLogout();
    } catch (e) {}

    signOut();
  };

  const menuItems = [
  // MAIN
  
  {
  title: "My Profile",
  icon: "person-circle-outline",
  route: "Profile",
  section: "MAIN",
},
  {
    title: "Attendance",
    icon: "calendar-outline",
    route: "Attendance",
    section: "MAIN",
  },
  
  {
    title: "Earnings",
    icon: "wallet-outline",
    route: "Earnings",
    section: "MAIN",
  },

  // ACCOUNT
  {
    title: "Holidays",
    icon: "calendar-clear-outline",
    route: "Holidays",
    section: "ACCOUNT",
  },
  {
    title: "Comp-off / OT",
    icon: "time-outline",
    route: "CompOff",
    section: "ACCOUNT",
  },
  {
    title: "My Performance",
    icon: "trending-up-outline",
    route: "Performance",
    section: "ACCOUNT",
  },
  {
    title: "My Onboarding",
    icon: "briefcase-outline",
    route: "Onboarding",
    section: "ACCOUNT",
  },
{
  title: "Policies & Guidelines",
  icon: "document-text-outline",
  route: "Policies",
  section: "ACCOUNT",
},
  // DANGER
  
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
  switch (item.route) {
    case "Home":
      navigation.navigate("EmployeeTabs", {
        screen: "Home",
        params: {
          screen: "Dashboard",
        },
      });
      break;

    case "Attendance":
  navigation.navigate("EmployeeTabs", {
    screen: "Attendance",
  });
  break;

    case "Leave":
      navigation.navigate("EmployeeTabs", {
        screen: "Leave",
      });
      break;
      
      case "CompOff":
  navigation.navigate("EmployeeTabs", {
    screen: "CompOff",
  });
  break;
  case "Earnings":
  navigation.navigate("EmployeeTabs", {
    screen: "Earnings",
  });
  break;
  case "Onboarding":
  navigation.navigate("EmployeeTabs", {
    screen: "Onboarding",
  });
  break;

  case "Profile":
  navigation.navigate("EmployeeTabs", {
    screen: "Profile",
  });
  break;

    case "Tickets":
      navigation.navigate("EmployeeTabs", {
        screen: "Tickets",
      });
      break;
      case "Holidays":
  navigation.navigate("EmployeeTabs", {
    screen: "Holidays",
  });
  break;

    case "Notifications":
      navigation.navigate("EmployeeTabs", {
        screen: "Notifications",
      });
      break;
      case "Performance":
  navigation.navigate("EmployeeTabs", {
    screen: "Performance",
  });
  break;
  case "Policies":
  navigation.navigate("EmployeeTabs", {
    screen: "Policies",
  });
  break;

    default:
      navigation.navigate(item.route);
  }

  navigation.closeDrawer();
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

        {renderSection("MAIN", "MAIN")}

{renderSection("ACCOUNT", "ACCOUNT")}



      </DrawerContentScrollView>
      <View style={styles.bottomContainer}>

    <TouchableOpacity
      style={styles.logoutButton}
      onPress={handleLogout}
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

    <Text style={styles.version}>
      Version 1.0.0
    </Text>

  </View>

    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F7F9FC",
  },

  scrollContent: {
    paddingBottom: 10,
  },

  header: {
    alignItems: "center",
    paddingTop: 8,
    paddingBottom: 12,
    paddingHorizontal: 24,
    backgroundColor: "#FFFFFF",
  },

  avatar: {
    width: 64,
    height: 64,
    borderRadius: 36,
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
  bottomContainer: {
  paddingHorizontal: 20,
  paddingTop: 8,
  paddingBottom: 18,
  backgroundColor: "#F7F9FC",
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
    fontSize: 20,
    fontWeight: "800",
    color: "#0F172A",
  },

  roleBadge: {
    marginTop: 12,

    backgroundColor: "#EEF4FF",

    paddingHorizontal: 16,
    paddingVertical: 5,

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
    marginVertical: 12,
    marginHorizontal: 20,
  },

  section: {
    marginBottom: 8,
    paddingHorizontal: 16,
  },

  sectionTitle: {
    marginBottom: 6,

    fontSize: 11,
    fontWeight: "700",

    color: "#94A3B8",

    letterSpacing: 1.2,

    marginLeft: 8,
  },

  menuItem: {
    height: 46,

    borderRadius: 14,

    paddingHorizontal: 16,

    marginBottom: 6,

    backgroundColor: "#FFFFFF",

    flexDirection: "row",

    alignItems: "center",

    shadowColor: "#000",
    shadowOpacity: 0.02,
    shadowRadius: 5,
    shadowOffset: {
      width: 0,
      height: 3,
    },

    elevation: 1,
  },

  activeMenuItem: {
    backgroundColor: "#173B8C",
    borderLeftWidth: 4,
    borderLeftColor: "#22C55E",
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