import React from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Image,
  StatusBar,
  Platform,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";
import { useNavigation, DrawerActions } from "@react-navigation/native";
import { useAuth } from "../../store/AuthContext";

export default function AdminHeader({
  title = "Dashboard",
  subtitle = "ADMIN PORTAL",
  profileImage,
  notificationCount = 3,
  onMenu,
  onNotification,
  onProfile,
}) {
  const navigation = useNavigation();
  const { user } = useAuth();
  const logoUri = profileImage || user?.logo;

  const handleMenuPress = () => {
    if (typeof onMenu === "function") {
      try {
        onMenu();
      } catch (e) {
        navigation.dispatch(DrawerActions.openDrawer());
      }
    } else {
      navigation.dispatch(DrawerActions.openDrawer());
    }
  };

  const handleProfilePress = () => {
    if (typeof onProfile === "function") {
      onProfile();
      return;
    }
    if (!navigation) return;

    try {
      const state = navigation.getState ? navigation.getState() : null;
      const routeNames = state?.routeNames || [];

      if (routeNames.includes("Settings")) {
        navigation.navigate("Settings", { tab: "profile" });
      } else if (routeNames.includes("Profile")) {
        navigation.navigate("Profile");
      } else {
        navigation.dispatch(DrawerActions.openDrawer());
      }
    } catch (_) {
      try {
        navigation.dispatch(DrawerActions.openDrawer());
      } catch (__) {}
    }
  };

  return (
    <>
      <StatusBar
        translucent
        backgroundColor="transparent"
        barStyle="dark-content"
      />
      <View style={styles.container}>
        {/* Hamburger Menu Button */}
        <TouchableOpacity
          activeOpacity={0.7}
          style={styles.iconButton}
          onPress={handleMenuPress}
        >
          <Ionicons name="menu-sharp" size={22} color="#0F172A" />
        </TouchableOpacity>

        {/* Header Title Section with Prominent Company Logo & Name */}
        <View style={styles.titleSection}>
          <View style={styles.headerCompanyRow}>
            <View style={styles.headerLogoBox}>
              {logoUri ? (
                <Image
                  source={{ uri: logoUri }}
                  style={styles.headerLogoImg}
                  resizeMode="cover"
                />
              ) : (
                <LinearGradient
                  colors={["#0B2253", "#173B8C"]}
                  style={styles.headerLogoGrad}
                >
                  <Text style={styles.headerLogoLetter}>
                    {(user?.company || "A").charAt(0).toUpperCase()}
                  </Text>
                </LinearGradient>
              )}
            </View>

            <View style={styles.headerTextGroup}>
              <Text numberOfLines={1} style={styles.headerCompanyText}>
                {(user?.company || subtitle).toUpperCase()}
              </Text>
              <Text numberOfLines={1} style={styles.title}>
                {title}
              </Text>
            </View>
          </View>
        </View>

        {/* Right Action Icons */}
        <View style={styles.rightGroup}>
          {onNotification && (
            <TouchableOpacity
              activeOpacity={0.7}
              style={styles.iconButton}
              onPress={onNotification}
            >
              <Ionicons
                name="notifications-outline"
                size={20}
                color="#0F172A"
              />
              {notificationCount > 0 && (
                <View style={styles.badge}>
                  <Text style={styles.badgeText}>
                    {notificationCount > 9 ? "9+" : notificationCount}
                  </Text>
                </View>
              )}
            </TouchableOpacity>
          )}

          <TouchableOpacity
            activeOpacity={0.8}
            style={styles.avatarButton}
            onPress={handleProfilePress}
          >
            {logoUri ? (
              <Image
                source={{ uri: logoUri }}
                style={styles.avatarImg}
                resizeMode="cover"
              />
            ) : (
              <View style={styles.avatarFallback}>
                <Text style={styles.avatarFallbackText}>
                  {(user?.company || user?.name || "A").charAt(0).toUpperCase()}
                </Text>
              </View>
            )}
          </TouchableOpacity>
        </View>
      </View>
    </>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 16,
    paddingTop: Platform.OS === "ios" ? 54 : (StatusBar.currentHeight || 24) + 12,
    paddingBottom: 14,
    backgroundColor: "#FFFFFF",
    borderBottomWidth: 1,
    borderBottomColor: "#F1F5F9",
    shadowColor: "#0F172A",
    shadowOpacity: 0.03,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 3 },
    elevation: 3,
  },
  iconButton: {
    width: 38,
    height: 38,
    borderRadius: 12,
    backgroundColor: "#F8FAFC",
    justify: "center",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#E2E8F0",
  },
  titleSection: {
    flex: 1,
    marginLeft: 10,
    marginRight: 10,
  },
  headerCompanyRow: {
    flexDirection: "row",
    alignItems: "center",
  },
  headerLogoBox: {
    width: 34,
    height: 34,
    borderRadius: 10,
    overflow: "hidden",
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "#F1F5F9",
    borderWidth: 1,
    borderColor: "#E2E8F0",
  },
  headerLogoImg: {
    width: "100%",
    height: "100%",
  },
  headerLogoGrad: {
    width: "100%",
    height: "100%",
    justifyContent: "center",
    alignItems: "center",
  },
  headerLogoLetter: {
    color: "#FFFFFF",
    fontWeight: "900",
    fontSize: 16,
  },
  headerTextGroup: {
    flex: 1,
    marginLeft: 8,
  },
  headerCompanyText: {
    fontSize: 10,
    fontWeight: "800",
    color: "#173B8C",
    letterSpacing: 0.6,
  },
  title: {
    fontSize: 16,
    fontWeight: "800",
    color: "#0F172A",
    letterSpacing: -0.3,
  },
  rightGroup: {
    flexDirection: "row",
    alignItems: "center",
  },
  badge: {
    position: "absolute",
    top: 4,
    right: 4,
    backgroundColor: "#EF4444",
    borderRadius: 8,
    minWidth: 16,
    height: 16,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 3,
  },
  badgeText: {
    color: "#FFFFFF",
    fontSize: 9,
    fontWeight: "800",
  },
  avatarButton: {
    marginLeft: 8,
  },
  avatarImg: {
    width: 34,
    height: 34,
    borderRadius: 17,
    backgroundColor: "#FFFFFF",
  },
  avatarFallback: {
    width: 34,
    height: 34,
    borderRadius: 17,
    backgroundColor: "#173B8C",
    justifyContent: "center",
    alignItems: "center",
  },
  avatarFallbackText: {
    color: "#FFFFFF",
    fontWeight: "900",
    fontSize: 14,
  },
});