import React from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Image,
  StatusBar,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

export default function AdminHeader({

  title = "Dashboard",

  profileImage,

  notificationCount = 3,

  onMenu,

  onNotification,

  onProfile,

}) {

  return (

    <>

      <StatusBar
        translucent
        backgroundColor="transparent"
        barStyle="dark-content"
      />

      <View style={styles.container}>

        <TouchableOpacity
          activeOpacity={0.8}
          style={styles.iconButton}
          onPress={onMenu}
        >

          <Ionicons
            name="menu"
            size={24}
            color="#0F172A"
          />

        </TouchableOpacity>

        <Text
          numberOfLines={1}
          style={styles.title}
        >
          {title}
        </Text>

        <View style={styles.right}>

          <TouchableOpacity
            activeOpacity={0.8}
            style={styles.iconButton}
            onPress={onNotification}
          >

            <Ionicons
              name="notifications-outline"
              size={22}
              color="#0F172A"
            />

            {notificationCount > 0 && (

              <View style={styles.badge}>

                <Text style={styles.badgeText}>
                  {notificationCount}
                </Text>

              </View>

            )}

          </TouchableOpacity>

          <TouchableOpacity
            activeOpacity={0.8}
            onPress={onProfile}
          >

            {profileImage ? (

              <Image
                source={{
                  uri: profileImage,
                }}
                style={styles.avatar}
              />

            ) : (

              <View style={styles.avatar}>

                <Ionicons
                  name="person"
                  size={22}
                  color="#2563EB"
                />

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

    paddingHorizontal: 22,

    paddingTop: 56,

    paddingBottom: 18,

    backgroundColor: "#F8FAFC",

  },

  title: {

    flex: 1,

    marginLeft: 18,

    fontSize: 30,

    fontWeight: "800",

    color: "#111827",

    letterSpacing: -0.8,

  },

  right: {

    flexDirection: "row",

    alignItems: "center",

  },

  iconButton: {

    width: 48,

    height: 48,

    borderRadius: 16,

    backgroundColor: "#FFFFFF",

    justifyContent: "center",

    alignItems: "center",

    borderWidth: 1,

    borderColor: "#E5E7EB",

    shadowColor: "#000",

    shadowOpacity: 0.06,

    shadowRadius: 10,

    shadowOffset: {

      width: 0,

      height: 5,

    },

    elevation: 4,

  },

  badge: {

    position: "absolute",

    top: 8,

    right: 8,

    minWidth: 18,

    height: 18,

    borderRadius: 9,

    backgroundColor: "#EF4444",

    justifyContent: "center",

    alignItems: "center",

    paddingHorizontal: 4,

  },

  badgeText: {

    color: "#FFFFFF",

    fontSize: 10,

    fontWeight: "700",

  },

  avatar: {

    marginLeft: 12,

    width: 48,

    height: 48,

    borderRadius: 24,

    backgroundColor: "#DBEAFE",

    justifyContent: "center",

    alignItems: "center",

    borderWidth: 2,

    borderColor: "#FFFFFF",

  },

});