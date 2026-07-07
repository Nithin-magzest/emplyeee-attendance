import React from "react";
import {
  View,
  TextInput,
  TouchableOpacity,
  StyleSheet,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

import THEME from "../../constants/theme";

export default function AdminSearchBar({
  value,
  onChangeText,
  placeholder = "Search...",
  onFilterPress,
}) {
  return (
    <View style={styles.container}>
      {/* Search Box */}

      <View style={styles.searchBox}>
        <Ionicons
          name="search"
          size={20}
          color={THEME.colors.textLight}
        />

        <TextInput
          value={value}
          onChangeText={onChangeText}
          placeholder={placeholder}
          placeholderTextColor={
            THEME.colors.textLight
          }
          style={styles.input}
        />
      </View>

      {/* Filter Button */}

      <TouchableOpacity
        activeOpacity={0.8}
        style={styles.filterButton}
        onPress={onFilterPress}
      >
        <Ionicons
          name="options-outline"
          size={22}
          color={THEME.colors.primary}
        />
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",

    alignItems: "center",

    marginBottom:
      THEME.spacing.sectionGap,
  },

  searchBox: {
    flex: 1,

    height: 54,

    flexDirection: "row",

    alignItems: "center",

    backgroundColor:
      THEME.colors.surface,

    borderRadius:
      THEME.radius.input,

    borderWidth: 1,

    borderColor:
      THEME.colors.border,

    paddingHorizontal: 16,

    ...THEME.shadows.sm,
  },

  input: {
    flex: 1,

    marginLeft: 12,

    color: THEME.colors.text,

    ...THEME.typography.body,
  },

  filterButton: {
    width: 54,

    height: 54,

    marginLeft: 12,

    borderRadius:
      THEME.radius.input,

    backgroundColor:
      THEME.colors.surface,

    borderWidth: 1,

    borderColor:
      THEME.colors.border,

    justifyContent: "center",

    alignItems: "center",

    ...THEME.shadows.sm,
  },
});