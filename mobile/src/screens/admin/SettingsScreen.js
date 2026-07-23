import React from "react";
import {
  SafeAreaView,
  ScrollView,
  StyleSheet,
  View,
  Text,
} from "react-native";
import Ionicons from "react-native-vector-icons/Ionicons";

import AdminHeader from "../../components/admin/AdminHeader";
import THEME from "../../constants/theme";

export default function SettingsScreen() {
  const renderSettingItem = (icon, title, subtitle) => {
    return (
      <View style={styles.settingItem}>
        <View style={styles.settingLeft}>
          <View style={styles.iconContainer}>
            <Ionicons
              name={icon}
              size={22}
              color={THEME.colors.primary}
            />
          </View>

          <View style={styles.settingContent}>
            <Text style={styles.settingTitle}>{title}</Text>
            <Text style={styles.settingSubtitle}>{subtitle}</Text>
          </View>
        </View>

        <Ionicons
          name="chevron-forward"
          size={20}
          color={THEME.colors.textLight}
        />
      </View>
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <AdminHeader title="Settings" />

      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.content}
      >
        {/* Profile */}
        <View style={styles.profileCard}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>A</Text>
          </View>

          <Text style={styles.name}>Administrator</Text>

          <Text style={styles.email}>admin@company.com</Text>
        </View>

        {/* General */}
        <View style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>General</Text>

          {renderSettingItem(
            "business-outline",
            "Company Settings",
            "Manage organization information"
          )}

          {renderSettingItem(
            "people-outline",
            "Employee Management",
            "Configure employee records"
          )}

          {renderSettingItem(
            "calendar-outline",
            "Attendance Settings",
            "Working hours & attendance rules"
          )}

          {renderSettingItem(
            "document-text-outline",
            "Leave Policies",
            "Manage leave types & approvals"
          )}
        </View>

        {/* Administration */}
        <View style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>Administration</Text>

          {renderSettingItem(
            "wallet-outline",
            "Payroll",
            "Salary & payroll configuration"
          )}

          {renderSettingItem(
            "notifications-outline",
            "Notifications",
            "Push & email preferences"
          )}

          {renderSettingItem(
            "shield-checkmark-outline",
            "Security",
            "Password, roles & permissions"
          )}

          {renderSettingItem(
            "cloud-upload-outline",
            "Backup & Restore",
            "Manage application backups"
          )}
        </View>

        {/* Support */}
        <View style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>Support</Text>

          {renderSettingItem(
            "help-circle-outline",
            "Help Center",
            "Documentation & FAQs"
          )}

          {renderSettingItem(
            "mail-outline",
            "Contact Support",
            "Reach our support team"
          )}

          {renderSettingItem(
            "information-circle-outline",
            "About Application",
            "Version, licenses & updates"
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: THEME.colors.background,
  },

  content: {
    paddingHorizontal: THEME.spacing.screenHorizontal,
    paddingTop: THEME.spacing.screenVertical,
    paddingBottom: 30,
  },

  profileCard: {
    backgroundColor: THEME.colors.card,
    borderRadius: THEME.radius.card,
    padding: 24,
    alignItems: "center",
    marginBottom: THEME.spacing.sectionGap,
    borderWidth: 1,
    borderColor: THEME.colors.border,
    ...THEME.shadows.md,
  },

  avatar: {
    width: 84,
    height: 84,
    borderRadius: 42,
    backgroundColor: THEME.colors.blueBg,
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 18,
  },

  avatarText: {
    fontSize: 32,
    fontWeight: "700",
    color: THEME.colors.primary,
  },

  name: {
    ...THEME.typography.headerTitle,
    color: THEME.colors.text,
  },

  email: {
    marginTop: 6,
    ...THEME.typography.body,
    color: THEME.colors.textSecondary,
  },

  sectionCard: {
    backgroundColor: THEME.colors.card,
    borderRadius: THEME.radius.card,
    borderWidth: 1,
    borderColor: THEME.colors.border,
    marginBottom: THEME.spacing.sectionGap,
    overflow: "hidden",
    ...THEME.shadows.sm,
  },

  sectionTitle: {
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 14,
    ...THEME.typography.cardTitle,
    color: THEME.colors.text,
  },

  settingItem: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 20,
    paddingVertical: 16,
    borderTopWidth: 1,
    borderTopColor: THEME.colors.border,
  },

  settingLeft: {
    flexDirection: "row",
    alignItems: "center",
    flex: 1,
  },

  iconContainer: {
    width: 46,
    height: 46,
    borderRadius: 12,
    backgroundColor: THEME.colors.blueBg,
    justifyContent: "center",
    alignItems: "center",
  },

  settingContent: {
    flex: 1,
    marginLeft: 16,
  },

  settingTitle: {
    ...THEME.typography.bodyMedium,
    color: THEME.colors.text,
    fontWeight: "600",
  },

  settingSubtitle: {
    marginTop: 4,
    ...THEME.typography.caption,
    color: THEME.colors.textSecondary,
  },
});