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
} from "../../api/client";

import { useAuth } from "../../store/AuthContext";

import LoadingSkeleton from "../../components/ui/LoadingSkeleton";
import EmptyState from "../../components/ui/EmptyState";

import EmployeeHeroCard from "../../components/employee/EmployeeHeroCard";
import EmployeeAttendanceCard from "../../components/employee/EmployeeAttendanceCard";
import EmployeeSummaryCards from "../../components/employee/EmployeeSummaryCards";
import EmployeeQuickActions from "../../components/employee/EmployeeQuickActions";
import EmployeeRecentAttendance from "../../components/employee/EmployeeRecentAttendance";
import EmployeeAnnouncementCard from "../../components/employee/EmployeeAnnouncementCard";
import EmployeeUpcomingEvents from "../../components/employee/EmployeeUpcomingEvents";

export default function EmployeeDashboard({ navigation }) {

<<<<<<< HEAD
export default function EmployeeDashboard({ navigation }) {
  const { signOut } = useAuth();
  const [data, setData]           = useState(null);
  const [loading, setLoading]     = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [checking, setChecking]   = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
=======
  const { signOut } = useAuth();
>>>>>>> 0ed281a (Redesign employee dashboard with professional SaaS UI)

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [checking, setChecking] = useState(false);
  const [data, setData] = useState(null);

  const loadDashboard = async () => {

    try {

      const res = await fetchEmployeePortal();
<<<<<<< HEAD
      if (res.data.ok) {
        setData(res.data);
        setUnreadCount(res.data.unread_notifications ?? 0);
      }
    } catch (e) {
      Alert.alert('Error', 'Failed to load portal.');
=======

      if (res.data.ok) {

        setData(res.data);

      }

    } catch {

      Alert.alert(
        "Error",
        "Unable to load dashboard."
      );

>>>>>>> 0ed281a (Redesign employee dashboard with professional SaaS UI)
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

          res.data.action === "login"
            ? "Checked In"
            : "Checked Out",

          `${res.data.status}\n${res.data.time}`

        );

        await loadDashboard();

      } else {

        Alert.alert(
          "Unable",
          res.data.msg
        );

      }

    } catch (e) {

      Alert.alert(
        "Error",
        e.response?.data?.msg || "Something went wrong."
      );

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

  if (loading) {

    return (

      <LinearGradient
        colors={[
          "#F8FAFC",
          "#F3F7FD",
          "#EDF4FF",
        ]}
        style={styles.loadingContainer}
      >

        <LoadingSkeleton />

      </LinearGradient>

    );

  }

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
<<<<<<< HEAD
        {/* Header */}
        <View style={styles.header}>
          <View>
            <Text style={styles.greeting}>👋 Hi, {data?.name}</Text>
            <Text style={styles.date}>{data?.today}</Text>
            <Text style={styles.empId}>{data?.employee_id}</Text>
          </View>
          <View style={styles.headerActions}>
            <TouchableOpacity onPress={() => navigation.navigate('Notifications')} style={styles.bellBtn}>
              <Ionicons name="notifications-outline" size={22} color="#fff" />
              {unreadCount > 0 && (
                <View style={styles.badge}>
                  <Text style={styles.badgeText}>{unreadCount > 99 ? '99+' : unreadCount}</Text>
                </View>
              )}
            </TouchableOpacity>
            <TouchableOpacity onPress={handleLogout} style={styles.logoutBtn}>
              <Ionicons name="log-out-outline" size={22} color={COLORS.redLight} />
            </TouchableOpacity>
          </View>
        </View>
=======
>>>>>>> 0ed281a (Redesign employee dashboard with professional SaaS UI)

        <EmployeeHeroCard
          employeeName={data?.name}
          designation={data?.designation}
          employeeId={data?.employee_id}
          date={data?.today}
          attendance={attendance}
          checking={checking}
          onCheckIn={handleCheckIn}
          onMenu={() => navigation.openDrawer()}
          onLogout={handleLogout}
        />

        <EmployeeAttendanceCard
          attendance={attendance}
        />

        <EmployeeSummaryCards
          hours={
            data?.today_hours || "08h 20m"
          }
          attendance={
            data?.attendance_percentage || "98%"
          }
          leaveBalance={
            data?.leave_balance || "08"
          }
          performance={
            data?.performance || "A+"
          }
        />

        <EmployeeQuickActions
          navigation={navigation}
        />
                {
          data?.recent_attendance?.length > 0 ? (

            <EmployeeRecentAttendance
              records={data.recent_attendance}
            />

          ) : (

            <EmptyState
              icon="calendar-outline"
              title="No Recent Attendance"
              subtitle="Your attendance history will appear here."
            />

          )
        }

        <EmployeeAnnouncementCard

          announcements={

            data?.announcements || []

          }

        />

        <EmployeeUpcomingEvents

          events={

            data?.upcoming_events || []

          }

        />

        <View
          style={styles.bottomSpacing}
        />

      </ScrollView>

    </LinearGradient>

  );

}
const styles = StyleSheet.create({

<<<<<<< HEAD
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 },
  greeting: { fontSize: 20, fontWeight: '700', color: '#fff' },
  date:     { fontSize: 13, color: COLORS.textMuted, marginTop: 2 },
  empId:    { fontSize: 12, color: COLORS.textDim, marginTop: 1 },
  headerActions: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  bellBtn:  { padding: 8, backgroundColor: COLORS.card, borderRadius: 10, borderWidth: 1, borderColor: COLORS.border },
  badge:    { position: 'absolute', top: -4, right: -4, backgroundColor: '#ef4444', borderRadius: 8, minWidth: 16, height: 16, justifyContent: 'center', alignItems: 'center', paddingHorizontal: 3 },
  badgeText:{ color: '#fff', fontSize: 9, fontWeight: '700' },
  logoutBtn:{ padding: 8, backgroundColor: COLORS.card, borderRadius: 10, borderWidth: 1, borderColor: COLORS.border },
=======
  container: {
>>>>>>> 0ed281a (Redesign employee dashboard with professional SaaS UI)

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
