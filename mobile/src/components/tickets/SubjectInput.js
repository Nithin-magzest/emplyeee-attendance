import React from "react";
import {
  View,
  Text,
  TextInput,
  StyleSheet,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

export default function SubjectInput({
  value,
  onChangeText,
}) {
  return (
    <View style={styles.container}>
      <Text style={styles.label}>
        Subject
      </Text>

      <View style={styles.inputContainer}>
        <Ionicons
          name="document-text-outline"
          size={20}
          color="#64748B"
        />

        <TextInput
          value={value}
          onChangeText={onChangeText}
          placeholder="Enter ticket subject"
          placeholderTextColor="#94A3B8"
          style={styles.input}
          maxLength={100}
        />
      </View>

      <Text style={styles.helper}>
        Keep the subject short and descriptive.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginBottom: 22,
  },

  label: {
    fontSize: 16,
    fontWeight: "800",
    color: "#0F172A",
    marginBottom: 12,
  },

  inputContainer: {
    flexDirection: "row",
    alignItems: "center",

    backgroundColor: "#FFFFFF",

    borderWidth: 1,
    borderColor: "#E2E8F0",

    borderRadius: 18,

    paddingHorizontal: 16,

    height: 58,

    shadowColor: "#000",
    shadowOpacity: 0.03,
    shadowRadius: 6,
    shadowOffset: {
      width: 0,
      height: 2,
    },

    elevation: 1,
  },

  input: {
    flex: 1,

    marginLeft: 12,

    fontSize: 15,

    color: "#0F172A",

    fontWeight: "600",
  },

  helper: {
    marginTop: 8,

    marginLeft: 2,

    fontSize: 12,

    color: "#94A3B8",

    fontWeight: "500",
  },
});