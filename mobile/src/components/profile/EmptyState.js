import React from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";

export default function EmptyState({
  icon = "folder-open-outline",
  title = "Nothing Here Yet",
  description = "There are no records available at the moment.",
  buttonText = "Add New",
  onPress = () => {},
  showButton = true,
}) {
  return (
    <View style={styles.card}>
      {/* Icon */}

      <View style={styles.iconContainer}>
        <Ionicons
          name={icon}
          size={54}
          color="#173B8C"
        />
      </View>

      {/* Title */}

      <Text style={styles.title}>
        {title}
      </Text>

      {/* Description */}

      <Text style={styles.description}>
        {description}
      </Text>

      {/* Button */}

      {showButton && (
        <TouchableOpacity
          activeOpacity={0.85}
          style={styles.button}
          onPress={onPress}
        >
          <Ionicons
            name="add-circle-outline"
            size={20}
            color="#FFFFFF"
          />

          <Text style={styles.buttonText}>
            {buttonText}
          </Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#FFFFFF",

    borderRadius: 24,

    paddingVertical: 42,
    paddingHorizontal: 28,

    alignItems: "center",

    borderWidth: 1,
    borderColor: "#E8EDF3",

    shadowColor: "#0F172A",
    shadowOpacity: 0.04,
    shadowRadius: 12,
    shadowOffset: {
      width: 0,
      height: 6,
    },

    elevation: 3,

    marginVertical: 16,
  },

  iconContainer: {
    width: 90,
    height: 90,

    borderRadius: 45,

    backgroundColor: "#EEF4FF",

    justifyContent: "center",
    alignItems: "center",

    marginBottom: 22,
  },

  title: {
    fontSize: 22,

    fontWeight: "800",

    color: "#0F172A",

    textAlign: "center",
  },

  description: {
    marginTop: 10,

    fontSize: 14,

    color: "#64748B",

    textAlign: "center",

    lineHeight: 22,

    paddingHorizontal: 12,
  },

  button: {
    marginTop: 28,

    flexDirection: "row",

    alignItems: "center",

    justifyContent: "center",

    backgroundColor: "#173B8C",

    borderRadius: 16,

    paddingHorizontal: 22,
    paddingVertical: 14,

    shadowColor: "#173B8C",
    shadowOpacity: 0.20,
    shadowRadius: 10,
    shadowOffset: {
      width: 0,
      height: 6,
    },

    elevation: 4,
  },

  buttonText: {
    marginLeft: 8,

    color: "#FFFFFF",

    fontSize: 15,

    fontWeight: "700",
  },
});