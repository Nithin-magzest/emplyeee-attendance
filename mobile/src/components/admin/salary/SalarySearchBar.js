import React from "react";

import {
  View,
  TextInput,
  TouchableOpacity,
  StyleSheet,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

import SALARY_THEME from "../../../constants/salaryTheme";

export default function SalarySearchBar({
  value,
  onChangeText,
  onClear,
  placeholder = "Search employee...",
}) {
  return (
    <View style={styles.container}>
      <View style={styles.searchContainer}>
        <Ionicons
          name="search-outline"
          size={20}
          color={SALARY_THEME.colors.textLight}
        />

        <TextInput
          value={value}
          onChangeText={onChangeText}
          placeholder={placeholder}
          placeholderTextColor={
            SALARY_THEME.colors.textLight
          }
          style={styles.input}
          autoCapitalize="none"
          autoCorrect={false}
          returnKeyType="search"
        />

        {value?.length > 0 && (
          <TouchableOpacity
            activeOpacity={0.7}
            onPress={onClear}
            style={styles.clearButton}
          >
            <Ionicons
              name="close-circle"
              size={20}
              color={SALARY_THEME.colors.textMuted}
            />
          </TouchableOpacity>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginBottom: 18,
  },

  searchContainer: {
    height: 54,

    flexDirection: "row",

    alignItems: "center",

    backgroundColor:
      SALARY_THEME.colors.surface,

    borderRadius:
      SALARY_THEME.radius.lg,

    paddingHorizontal: 16,

    borderWidth: 1,

    borderColor:
      SALARY_THEME.colors.border,

    ...SALARY_THEME.shadow,
  },

  input: {
    flex: 1,

    marginLeft: 10,

    fontSize: 15,

    color:
      SALARY_THEME.colors.textPrimary,
  },

  clearButton: {
    marginLeft: 8,

    padding: 2,
  },
});