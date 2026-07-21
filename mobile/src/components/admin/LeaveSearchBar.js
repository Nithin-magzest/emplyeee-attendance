import React from "react";

import {
  View,
  TextInput,
  TouchableOpacity,
  StyleSheet,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

import LEAVE_THEME from "../../constants/leaveTheme";

export default function LeaveSearchBar({
  value,
  onChangeText,
  onFilterPress,
  onClear,
}) {
  return (
    <View style={styles.container}>
      <View style={styles.searchContainer}>
        <Ionicons
          name="search"
          size={20}
          color={LEAVE_THEME.colors.textMuted}
        />

        <TextInput
          value={value}
          onChangeText={onChangeText}
          placeholder="Search employee, leave type..."
          placeholderTextColor={
            LEAVE_THEME.colors.textLight
          }
          style={styles.input}
        />

        {value?.length > 0 && (
          <TouchableOpacity
            activeOpacity={0.8}
            onPress={onClear}
          >
            <Ionicons
              name="close-circle"
              size={20}
              color={LEAVE_THEME.colors.textMuted}
            />
          </TouchableOpacity>
        )}
      </View>

      <TouchableOpacity
        activeOpacity={0.85}
        style={styles.filterButton}
        onPress={onFilterPress}
      >
        <Ionicons
          name="options-outline"
          size={22}
          color="#FFFFFF"
        />
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({

  container: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 18,
  },

  searchContainer: {
    flex: 1,

    height: 56,

    backgroundColor: "#FFFFFF",

    borderRadius: 18,

    borderWidth: 1,

    borderColor: LEAVE_THEME.colors.border,

    flexDirection: "row",

    alignItems: "center",

    paddingHorizontal: 16,

    ...LEAVE_THEME.shadow,
  },

  input: {
    flex: 1,

    marginLeft: 12,

    fontSize: 15,

    color: LEAVE_THEME.colors.textPrimary,
  },

  filterButton: {
    width: 56,

    height: 56,

    marginLeft: 12,

    borderRadius: 18,

    backgroundColor: LEAVE_THEME.colors.primary,

    justifyContent: "center",

    alignItems: "center",

    ...LEAVE_THEME.shadow,
  },

});