import React, { useState, useCallback } from "react";
import {
  ScrollView,
  StyleSheet,
  RefreshControl,
  Alert,
  View,
} from "react-native";

import { LinearGradient } from "expo-linear-gradient";
import { useFocusEffect } from "@react-navigation/native";

import {
  fetchEmployeePortal,
  employeeCheckin,
  employeeLogout,
  getPhotoUrl,
} from "../../api/client";

import { useAuth } from "../../store/AuthContext";

import LoadingSkeleton from "../../components/ui/LoadingSkeleton";
import EmptyState from "../../components/ui/EmptyState";
import AttendanceScannerModal from "../AttendanceScannerModal";

import EmployeeHeroCard from "../../components/employee/EmployeeHeroCard";
import EmployeeAttendanceCard from "../../components/employee/EmployeeAttendanceCard";
import EmployeeSummaryCards from "../../components/employee/EmployeeSummaryCards";
import EmployeeQuickActions from "../../components/employee/EmployeeQuickActions";
import EmployeeRecentAttendance from "../../components/employee/EmployeeRecentAttendance";
import EmployeeAnnouncementCard from "../../components/employee/EmployeeAnnouncementCard";
import EmployeeUpcomingEvents from "../../components/employee/EmployeeUpcomingEvents";

export default function EmployeeDashboard({ navigation }) {

  const { signOut } = useAuth();

  const [loading, setLoading]       = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [checking, setChecking]     = useState(false);
  const [data, setData]             = useState(null);
  const [showScanner, setShowScanner] = useState(false);

  const loadDashboard = async () => {
    try {
      const res = await fetchEmployeePortal();
      if (res.data.ok) {
        setData(res.data);
      }
    } catch {
      Alert.alert("Error", "Unable to load dashboard.");
    }
    setLoading(false);
    setRefreshing(false);
  };

  useFocusEffect(
    useCallback(() => {
      loadDashboard();
    }, [])
  );

  const handleCheckIn = async () => {
    setChecking(true);
    try {
      const res = await employeeCheckin();
      if (res.data.ok) {
        Alert.alert(
          res.data.action === "login" ? "Checked In" : "Checked Out",
          `${res.data.status}\n${res.data.time}`
        );
        await loadDashboard();
      } else {
        Alert.alert("Unable", res.data.msg);
      }
    } catch (e) {
      Alert.alert("Error", e.response?.data?.msg || "Something went wrong.");
    }
    setChecking(false);
  };

  const handleLogout = async () => {
    try {
      await employeeLogout();
    } catch {}
    signOut();
  };

  const attendance = data?.today_attendance;
  const photoUrl   = data?.employee_id ? getPhotoUrl(data.employee_id) : null;

  if (loading) {
    return (
      <LinearGradient
        colors={["#F8FAFC", "#F3F7FD", "#EDF4FF"]}
        style={styles.loadingContainer}
      >
        <LoadingSkeleton />
      </LinearGradient>
    );
  }

  return (
    <LinearGradient
      colors={["#F8FAFC", "#F3F7FD", "#EDF4FF"]}
      start={{ x: 0, y: 0 }}
      end={{ x: 1, y: 1 }}
      style={styles.container}
    >
      <AttendanceScannerModal
        visible={showScanner}
        onClose={() => setShowScanner(false)}
        onSuccess={() => loadDashboard()}
      />
      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => {
              setRefreshing(true);
              loadDashboard();
            }}
            colors={["#173B8C"]}
            tintColor="#173B8C"
          />
        }
      >
        <EmployeeHeroCard
          employeeName={data?.name}
          designation={data?.role || data?.designation}
          employeeId={data?.employee_id}
          date={data?.today}
          attendance={attendance}
          checking={checking}
          onCheckIn={handleCheckIn}
          onLogout={handleLogout}
          photoUrl={photoUrl}
          onScanQR={() => setShowScanner(true)}
        />

        <EmployeeAttendanceCard attendance={attendance} />

        <EmployeeSummaryCards
          hours={data?.today_hours || "08h 20m"}
          attendance={data?.attendance_percentage || "98%"}
          leaveBalance={data?.leave_balance || "08"}
          performance={data?.performance || "A+"}
        />

        <EmployeeQuickActions navigation={navigation} />

        {data?.recent_attendance?.length > 0 ? (
          <EmployeeRecentAttendance records={data.recent_attendance} />
        ) : (
          <EmptyState
            icon="calendar-outline"
            title="No Recent Attendance"
            subtitle="Your attendance history will appear here."
          />
        )}

        <EmployeeAnnouncementCard announcements={data?.announcements || []} />

        <EmployeeUpcomingEvents events={data?.upcoming_events || []} />

        <View style={styles.bottomSpacing} />

      </ScrollView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "#F8FAFC",
  },
  content: {
    paddingHorizontal: 20,
    paddingTop: 55,
    paddingBottom: 120,
  },
  bottomSpacing: {
    height: 30,
  },
});
