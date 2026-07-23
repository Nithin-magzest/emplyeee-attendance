import React from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useNavigation } from "@react-navigation/native";

export default function ProfileHeader({
  title = "My Profile",
  subtitle = "",
  showBack = false,
}) {
      const navigation = useNavigation();

  const today = new Date();

  const formattedDate = today.toLocaleDateString("en-US", {
    weekday: "long",
    day: "numeric",
    month: "long",
  });

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.container}>
        {/* Left */}

        <TouchableOpacity
  activeOpacity={0.8}
  style={styles.iconButton}
  onPress={() => {
    if (showBack) {
      navigation.goBack();
    } else {
      navigation.openDrawer();
    }
  }}
>
  <Ionicons
    name={showBack ? "arrow-back" : "menu"}
    size={22}
    color="#173B8C"
  />
</TouchableOpacity>
        {/* Center */}

        <View style={styles.center}>
          <Text style={styles.subtitle}>
            {subtitle}
          </Text>

          <Text style={styles.title}>
            {title}
          </Text>

          <Text style={styles.date}>
            {formattedDate}
          </Text>
        </View>

        {/* Right */}

        <TouchableOpacity
          activeOpacity={0.8}
          style={styles.iconButton}
        >
          <Ionicons
            name="person-circle-outline"
            size={26}
            color="#173B8C"
          />
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    backgroundColor: "#F8FAFC",
  },

  container: {
  flexDirection: "row",
  alignItems: "center",
  justifyContent: "space-between",

  paddingHorizontal: 20,
  paddingTop: 16,
  paddingBottom: 20,

  marginTop: 16, // Pushes the whole header down
},

  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 12,
  },

  subtitle: {
    fontSize: 12,
    color: "#64748B",
    fontWeight: "600",
    letterSpacing: 0.3,
  },

  title: {
    marginTop: 3,
    fontSize: 18,
    fontWeight: "800",
    color: "#111827",
    letterSpacing: -0.8,
  },

  date: {
    marginTop: 4,
    fontSize: 13,
    color: "#94A3B8",
    fontWeight: "500",
  },

  iconButton: {
    width: 46,
    height: 46,

    borderRadius: 14,

    backgroundColor: "#FFFFFF",

    justifyContent: "center",
    alignItems: "center",

    borderWidth: 1,
    borderColor: "#E8EDF3",

    shadowColor: "#0F172A",
    shadowOpacity: 0.05,
    shadowRadius: 10,
    shadowOffset: {
      width: 0,
      height: 4,
    },

    elevation: 3,
  },
});