import React, { useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { Ionicons } from "@expo/vector-icons";
import { changePassword } from "../../api/client";

export default function ChangePinScreen({ navigation }) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);

  const handleChangePassword = async () => {
    if (!currentPassword || !newPassword || !confirmPassword) {
      Alert.alert("Error", "Please fill in all fields.");
      return;
    }
    if (newPassword.length < 4) {
      Alert.alert("Error", "New password must be at least 4 characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      Alert.alert("Error", "New password and confirm password do not match.");
      return;
    }
    if (newPassword === currentPassword) {
      Alert.alert("Error", "New password must be different from your current password.");
      return;
    }

    setLoading(true);
    try {
      const res = await changePassword(currentPassword, newPassword);
      if (res.data.ok) {
        Alert.alert("Success", "Password changed successfully!", [
          { text: "OK", onPress: () => navigation.goBack() },
        ]);
      } else {
        Alert.alert("Failed", res.data.msg || "Unable to change password.");
      }
    } catch (e) {
      Alert.alert("Error", e.response?.data?.msg || "Something went wrong.");
    }
    setLoading(false);
  };

  return (
    <LinearGradient
      colors={["#F8FAFC", "#F3F7FD", "#EDF4FF"]}
      style={styles.container}
    >
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        style={{ flex: 1 }}
      >
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">

          <View style={styles.header}>
            <TouchableOpacity style={styles.backBtn} onPress={() => navigation.goBack()}>
              <Ionicons name="arrow-back" size={22} color="#173B8C" />
            </TouchableOpacity>
            <View style={styles.iconCircle}>
              <Ionicons name="lock-closed" size={28} color="#fff" />
            </View>
            <Text style={styles.title}>Change Password</Text>
            <Text style={styles.subtitle}>Update your login password</Text>
          </View>

          <View style={styles.card}>

            <Text style={styles.label}>Current Password</Text>
            <View style={styles.inputRow}>
              <Ionicons name="lock-closed-outline" size={18} color="#64748B" style={styles.icon} />
              <TextInput
                style={styles.input}
                placeholder="Enter current password"
                placeholderTextColor="#94A3B8"
                value={currentPassword}
                onChangeText={setCurrentPassword}
                secureTextEntry={!showCurrent}
                autoCapitalize="none"
                autoCorrect={false}
              />
              <TouchableOpacity onPress={() => setShowCurrent(!showCurrent)} style={styles.eyeBtn}>
                <Ionicons
                  name={showCurrent ? "eye-off-outline" : "eye-outline"}
                  size={20}
                  color="#64748B"
                />
              </TouchableOpacity>
            </View>

            <Text style={styles.label}>New Password</Text>
            <View style={styles.inputRow}>
              <Ionicons name="key-outline" size={18} color="#64748B" style={styles.icon} />
              <TextInput
                style={styles.input}
                placeholder="Enter new password"
                placeholderTextColor="#94A3B8"
                value={newPassword}
                onChangeText={setNewPassword}
                secureTextEntry={!showNew}
                autoCapitalize="none"
                autoCorrect={false}
              />
              <TouchableOpacity onPress={() => setShowNew(!showNew)} style={styles.eyeBtn}>
                <Ionicons
                  name={showNew ? "eye-off-outline" : "eye-outline"}
                  size={20}
                  color="#64748B"
                />
              </TouchableOpacity>
            </View>

            <Text style={styles.label}>Confirm New Password</Text>
            <View style={styles.inputRow}>
              <Ionicons name="checkmark-circle-outline" size={18} color="#64748B" style={styles.icon} />
              <TextInput
                style={styles.input}
                placeholder="Re-enter new password"
                placeholderTextColor="#94A3B8"
                value={confirmPassword}
                onChangeText={setConfirmPassword}
                secureTextEntry
                autoCapitalize="none"
                autoCorrect={false}
              />
            </View>

            <TouchableOpacity
              style={[styles.btn, loading && styles.btnDisabled]}
              onPress={handleChangePassword}
              disabled={loading}
            >
              {loading ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.btnTxt}>Update Password</Text>
              )}
            </TouchableOpacity>

          </View>

          <View style={styles.hint}>
            <Ionicons name="information-circle-outline" size={16} color="#64748B" />
            <Text style={styles.hintTxt}>
              Your default password is <Text style={styles.hintBold}>1234</Text>. Change it to something secure.
            </Text>
          </View>

        </ScrollView>
      </KeyboardAvoidingView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: {
    flexGrow: 1,
    paddingHorizontal: 20,
    paddingTop: 55,
    paddingBottom: 40,
  },
  header: {
    alignItems: "center",
    marginBottom: 28,
  },
  backBtn: {
    alignSelf: "flex-start",
    padding: 6,
    marginBottom: 16,
  },
  iconCircle: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: "#173B8C",
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 14,
    shadowColor: "#173B8C",
    shadowOpacity: 0.3,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 6 },
    elevation: 8,
  },
  title: {
    fontSize: 24,
    fontWeight: "700",
    color: "#0F172A",
  },
  subtitle: {
    marginTop: 6,
    fontSize: 13,
    color: "#64748B",
  },
  card: {
    backgroundColor: "#FFFFFF",
    borderRadius: 20,
    padding: 22,
    shadowColor: "#0F172A",
    shadowOpacity: 0.07,
    shadowRadius: 20,
    shadowOffset: { width: 0, height: 8 },
    elevation: 6,
  },
  label: {
    fontSize: 12,
    fontWeight: "600",
    color: "#475569",
    marginBottom: 8,
  },
  inputRow: {
    flexDirection: "row",
    alignItems: "center",
    height: 52,
    borderRadius: 12,
    backgroundColor: "#F8FAFC",
    borderWidth: 1,
    borderColor: "#E2E8F0",
    paddingHorizontal: 14,
    marginBottom: 18,
  },
  icon: { marginRight: 10 },
  input: {
    flex: 1,
    fontSize: 15,
    color: "#0F172A",
  },
  eyeBtn: {
    width: 36,
    height: 36,
    justifyContent: "center",
    alignItems: "center",
  },
  btn: {
    height: 50,
    borderRadius: 12,
    backgroundColor: "#173B8C",
    justifyContent: "center",
    alignItems: "center",
    marginTop: 6,
  },
  btnDisabled: {
    opacity: 0.6,
  },
  btnTxt: {
    fontSize: 15,
    fontWeight: "700",
    color: "#FFFFFF",
  },
  hint: {
    flexDirection: "row",
    alignItems: "flex-start",
    marginTop: 20,
    paddingHorizontal: 4,
    gap: 8,
  },
  hintTxt: {
    flex: 1,
    fontSize: 13,
    color: "#64748B",
    lineHeight: 20,
  },
  hintBold: {
    fontWeight: "700",
    color: "#173B8C",
  },
});
