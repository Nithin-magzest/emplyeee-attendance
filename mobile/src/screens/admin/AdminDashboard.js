import React, { useState } from "react";
import {
  SafeAreaView,
  ScrollView,
  StyleSheet,
  View,
  RefreshControl,
} from "react-native";
import { DrawerActions } from "@react-navigation/native";
import { LinearGradient } from "expo-linear-gradient";

import THEME from "../../constants/theme";

import AdminHeader from "../../components/admin/AdminHeader";
import AdminSearchBar from "../../components/admin/AdminSearchBar";
import DashboardHeroCard from "../../components/admin/DashboardHeroCard";

import PendingApprovalCard from "../../components/admin/PendingApprovalCard";
import AttendanceOverviewCard from "../../components/admin/AttendanceOverviewCard";
import QuickActionGrid from "../../components/admin/QuickActionGrid";
import RecentActivityList from "../../components/admin/RecentActivityList";
import AnnouncementCard from "../../components/admin/AnnouncementCard";
import AnalyticsOverviewCard from "../../components/admin/AnalyticsOverviewCard";

export default function AdminDashboard({ navigation }) {

  const [search, setSearch] = useState("");

  const [refreshing, setRefreshing] =
    useState(false);

  const onRefresh = () => {
    setRefreshing(true);

    setTimeout(() => {
      setRefreshing(false);
    }, 1200);
  };

  return (

    <LinearGradient
      colors={[
        "#F8FAFC",
        "#F3F7FD",
        "#EDF4FF",
      ]}
      start={{ x: 0, y: 0 }}
      end={{ x: 1, y: 1 }}
      style={styles.container}
    >

      <SafeAreaView style={{ flex: 1 }}>

        <AdminHeader
    title="Dashboard"
    onMenu={() =>
        navigation.dispatch(
            DrawerActions.openDrawer()
        )
    }
/>

        <ScrollView
          showsVerticalScrollIndicator={false}
          contentContainerStyle={
            styles.content
          }
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={onRefresh}
              colors={[
                THEME.colors.primary,
              ]}
            />
          }
        >

          <DashboardHeroCard
            adminName="Administrator"
            company="HR Management System"
            totalEmployees={254}
            present={228}
          />

          <AdminSearchBar
            value={search}
            onChangeText={setSearch}
            placeholder="Search employees..."
          />

          <View style={styles.sectionSpacing} />

        

          <AttendanceOverviewCard />

          <QuickActionGrid
            navigation={navigation}
          />

          <PendingApprovalCard
            title="Leave Requests"
            pending={8}
            subtitle="Requires your approval"
            icon="document-text-outline"
            color="#F59E0B"
            background="#FEF3C7"
          />

          <PendingApprovalCard
            title="Payroll Approval"
            pending={3}
            subtitle="Waiting for verification"
            icon="wallet-outline"
            color="#8B5CF6"
            background="#EDE9FE"
          />
                    <AnalyticsOverviewCard />

          <AnnouncementCard />

          <RecentActivityList />

          <View style={styles.bottomSpacing} />

        </ScrollView>

      </SafeAreaView>

    </LinearGradient>
  );
}

const styles = StyleSheet.create({

  container: {
    flex: 1,
  },

  content: {
    paddingHorizontal: 20,
    paddingBottom: 120,
  },

  sectionSpacing: {
    height: 20,
  },

  statsGrid: {
    flexDirection: "row",

    flexWrap: "wrap",

    justifyContent: "space-between",

    marginBottom: 24,
  },

  heroSpacing: {
    marginBottom: 24,
  },

  cardSpacing: {
    marginBottom: 22,
  },

  row: {
    flexDirection: "row",

    justifyContent: "space-between",

    alignItems: "center",
  },

  sectionHeader: {
    flexDirection: "row",

    justifyContent: "space-between",

    alignItems: "center",

    marginBottom: 18,
  },

  sectionTitle: {
    fontSize: 22,

    fontWeight: "800",

    color: "#0F172A",
  },

  sectionSubtitle: {
    marginTop: 6,

    fontSize: 13,

    color: "#64748B",

    fontWeight: "500",
  },

  viewAll: {
    color: THEME.colors.primary,

    fontSize: 14,

    fontWeight: "700",
  },

  dashboardCard: {
    backgroundColor: "#FFFFFF",

    borderRadius: 24,

    padding: 20,

    borderWidth: 1,

    borderColor: "#E8EDF5",

    shadowColor: "#000",

    shadowOpacity: 0.05,

    shadowRadius: 12,

    shadowOffset: {
      width: 0,
      height: 6,
    },

    elevation: 4,
  },
    statsCard: {
    width: "48%",
    marginBottom: 16,
  },

  quickActionSpacing: {
    marginTop: 8,
    marginBottom: 28,
  },

  analyticsSpacing: {
    marginBottom: 28,
  },

  announcementSpacing: {
    marginBottom: 28,
  },

  activitySpacing: {
    marginBottom: 28,
  },

  pendingSpacing: {
    marginBottom: 20,
  },

  divider: {
    height: 1,
    backgroundColor: "#E8EDF5",
    marginVertical: 24,
  },

  emptyContainer: {
    backgroundColor: "#FFFFFF",

    borderRadius: 22,

    padding: 24,

    justifyContent: "center",

    alignItems: "center",

    borderWidth: 1,

    borderColor: "#E8EDF5",
  },

  emptyText: {
    marginTop: 12,

    fontSize: 15,

    color: "#64748B",

    fontWeight: "600",
  },

  bottomSpacing: {
    height: 120,
  },

});