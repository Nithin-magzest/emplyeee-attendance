import React from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";
import { DrawerActions, useNavigation } from "@react-navigation/native";

import THEME from "../../constants/theme";

export default function AdminHeader({
  title = "Dashboard",
  showNotification = true,
  onNotificationPress,
}) {
  const navigation = useNavigation();

  return (
    <View style={styles.container}>
      {/* Left */}

      <View style={styles.leftSection}>
        <TouchableOpacity
          activeOpacity={0.7}
          style={styles.menuButton}
          onPress={() =>
            navigation.dispatch(
              DrawerActions.openDrawer()
            )
          }
        >
          <Ionicons
            name="menu"
            size={24}
            color={THEME.colors.text}
          />
        </TouchableOpacity>

        <Text style={styles.title}>
          {title}
        </Text>
      </View>

      {/* Right */}

      <View style={styles.rightSection}>
        {showNotification && (
          <TouchableOpacity
            activeOpacity={0.7}
            style={styles.notificationButton}
            onPress={onNotificationPress}
          >
            <Ionicons
              name="notifications-outline"
              size={22}
              color={THEME.colors.text}
            />

            <View style={styles.badge}>
              <Text style={styles.badgeText}>
                3
              </Text>
            </View>
          </TouchableOpacity>
        )}

        <TouchableOpacity
          activeOpacity={0.7}
          style={styles.avatar}
        >
          <Ionicons
            name="person"
            size={20}
            color={THEME.colors.primary}
          />
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    height: THEME.spacing.headerHeight,

    backgroundColor:
      THEME.colors.surface,

    flexDirection: "row",

    alignItems: "center",

    justifyContent:
      "space-between",

    paddingHorizontal:
      THEME.spacing.screenHorizontal,

    borderBottomWidth: 1,

    borderBottomColor:
      THEME.colors.border,

    ...THEME.shadows.header,
  },

  leftSection: {
    flexDirection: "row",

    alignItems: "center",
  },

  rightSection: {
    flexDirection: "row",

    alignItems: "center",
  },

  menuButton: {
    width: 42,

    height: 42,

    borderRadius:
      THEME.radius.button,

    backgroundColor:
      THEME.colors.blueBg,

    justifyContent: "center",

    alignItems: "center",
  },

  title: {
    marginLeft: 14,

    ...THEME.typography.headerTitle,

    color: THEME.colors.text,
  },

  notificationButton: {
    width: 42,

    height: 42,

    borderRadius:
      THEME.radius.button,

    backgroundColor:
      THEME.colors.surface,

    borderWidth: 1,

    borderColor:
      THEME.colors.border,

    justifyContent: "center",

    alignItems: "center",

    marginRight: 12,
  },

  badge: {
    position: "absolute",

    top: 6,

    right: 5,

    width: 16,

    height: 16,

    borderRadius: 8,

    backgroundColor:
      THEME.colors.danger,

    justifyContent: "center",

    alignItems: "center",
  },

  badgeText: {
    color: "#FFFFFF",

    fontSize: 9,

    fontWeight: "700",
  },

  avatar: {
    width: 42,

    height: 42,

    borderRadius: 21,

    backgroundColor:
      THEME.colors.primaryLight,

    justifyContent: "center",

    alignItems: "center",
  },
});