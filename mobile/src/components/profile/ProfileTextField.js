import React from "react";
import {
  View,
  Text,
  TextInput,
  StyleSheet,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";

export default function ProfileTextField({
  label = "Full Name",
  value = "",
  placeholder = "Enter value",
  icon = "person-outline",
  keyboardType = "default",
  editable = true,
  secureTextEntry = false,
  multiline = false,
  numberOfLines = 1,
  error = "",
  onChangeText = () => {},
}) {
  return (
    <View style={styles.container}>
      {/* Label */}

      <Text style={styles.label}>
        {label}
      </Text>

      {/* Input */}

      <View
        style={[
          styles.inputContainer,
          !editable && styles.disabledInput,
          error ? styles.errorBorder : null,
        ]}
      >
        <Ionicons
          name={icon}
          size={20}
          color="#64748B"
          style={styles.icon}
        />

        <TextInput
          value={value}
          placeholder={placeholder}
          placeholderTextColor="#94A3B8"
          editable={editable}
          keyboardType={keyboardType}
          secureTextEntry={secureTextEntry}
          multiline={multiline}
          numberOfLines={numberOfLines}
          onChangeText={onChangeText}
          style={[
            styles.input,
            multiline && styles.multilineInput,
          ]}
        />
      </View>

      {/* Error */}

      {error ? (
        <View style={styles.errorRow}>
          <Ionicons
            name="alert-circle"
            size={14}
            color="#EF4444"
          />

          <Text style={styles.errorText}>
            {error}
          </Text>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginBottom: 20,
  },

  label: {
    marginBottom: 8,

    fontSize: 13,

    fontWeight: "700",

    color: "#334155",

    letterSpacing: 0.2,
  },

  inputContainer: {
    flexDirection: "row",

    alignItems: "center",

    backgroundColor: "#FFFFFF",

    borderRadius: 16,

    borderWidth: 1,

    borderColor: "#E2E8F0",

    paddingHorizontal: 16,

    minHeight: 56,

    shadowColor: "#0F172A",

    shadowOpacity: 0.03,

    shadowRadius: 8,

    shadowOffset: {
      width: 0,
      height: 3,
    },

    elevation: 2,
  },

  disabledInput: {
    backgroundColor: "#F8FAFC",
  },

  errorBorder: {
    borderColor: "#EF4444",
  },

  icon: {
    marginRight: 12,
  },

  input: {
    flex: 1,

    fontSize: 15,

    color: "#0F172A",

    fontWeight: "500",

    paddingVertical: 16,
  },

  multilineInput: {
    minHeight: 110,

    textAlignVertical: "top",
  },

  errorRow: {
    flexDirection: "row",

    alignItems: "center",

    marginTop: 8,
  },

  errorText: {
    marginLeft: 6,

    fontSize: 12,

    color: "#EF4444",

    fontWeight: "600",
  },
});