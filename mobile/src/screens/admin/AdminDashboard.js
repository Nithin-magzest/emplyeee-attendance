import React, { useState, useCallback } from "react";
import {
  ScrollView,
  StyleSheet,
  RefreshControl,
  ActivityIndicator,
  Alert,
  View,
} from "react-native";

import { LinearGradient } from "expo-linear-gradient";
import { useFocusEffect } from "@react-navigation/native";

import { fetchDashboard, adminLogout } from "../../api/client";
import { useAuth } from "../../store/AuthContext";
import { COLORS } from "../../config";

import DashboardHeader from "../../components/dashboard/DashboardHeader";
import DashboardStats from "../../components/dashboard/DashboardStats";
import ModuleGrid from "../../components/dashboard/ModuleGrid";
import PendingCard from "../../components/dashboard/PendingCard";
import AttendanceCard from "../../components/dashboard/AttendanceCard";
import DashboardActivity from "../../components/dashboard/DashboardActivity";

import SectionHeader from "../../components/ui/SectionHeader";
import EmptyState from "../../components/ui/EmptyState";
import LoadingSkeleton from "../../components/ui/LoadingSkeleton";

<<<<<<< HEAD
export default function AdminDashboard({ navigation }) {
  const { signOut, user } = useAuth();
  const [data, setData]         = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [loading, setLoading]   = useState(true);
  const [unreadCount, setUnreadCount] = useState(0);

  const load = async () => {
    try {
      const res = await fetchDashboard();
      if (res.data.ok) {
        setData(res.data);
        setUnreadCount(res.data.unread_notifications ?? 0);
      }
    } catch (e) {
      Alert.alert('Error', 'Failed to load dashboard.');
    }
    setLoading(false);
    setRefreshing(false);
  };
=======
export default function AdminDashboard() {

    const { signOut } = useAuth();
>>>>>>> 0ed281a (Redesign employee dashboard with professional SaaS UI)

    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [data, setData] = useState(null);

    const loadDashboard = async () => {

        try {

            const res = await fetchDashboard();

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

<<<<<<< HEAD
  return (
    <LinearGradient colors={COLORS.adminBg} style={styles.bg}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(); }} tintColor="#fff" />}
      >
        {/* Header */}
        <View style={styles.header}>
          <View>
            <Text style={styles.greeting}>👋 Welcome, Admin</Text>
            <Text style={styles.date}>{data?.today || ''}</Text>
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
    const handleLogout = async () => {
>>>>>>> 0ed281a (Redesign employee dashboard with professional SaaS UI)

        try {
            await adminLogout();
        } catch {}

        signOut();

    };

    if (loading) {

        return (
            <LinearGradient
                colors={COLORS.adminBg}
                style={styles.loadingContainer}
            >
                <LoadingSkeleton />
            </LinearGradient>
        );

    }

    return (

        <LinearGradient
  colors={[
    "#F6F9FF",
    "#EDF4FF",
    "#E8F0FF",
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

                        tintColor="#fff"

                        onRefresh={() => {

                            setRefreshing(true);

                            loadDashboard();

                        }}

                    />

                }

            >

                <DashboardHeader
                    date={data?.today}
                    onLogout={handleLogout}
                />

                <DashboardStats
                    total={data?.total}
                    present={data?.present}
                    absent={data?.absent}
                    late={data?.late}
                />

                <ModuleGrid />

                <PendingCard
                    pendingLeaves={data?.pending_leaves}
                    pendingResignations={data?.pending_resignations}
                />

                <SectionHeader
                    title="Today's Attendance"
                    subtitle="Employees checked in today"
                />

                {
                    data?.today_rows?.length > 0
                    ?

                    data.today_rows.map(employee => (

                        <AttendanceCard

                            key={employee.employee_id}

                            employee={employee}

                        />

                    ))

                    :

                    <EmptyState

                        icon="people-outline"

                        title="No Attendance"

                        subtitle="No employees have checked in today."

                    />

                }

                <DashboardActivity />

                <View style={{height:40}}/>

            </ScrollView>

        </LinearGradient>

    );

}

const styles = StyleSheet.create({

<<<<<<< HEAD
  header: {
    flexDirection: 'row', justifyContent: 'space-between',
    alignItems: 'flex-start', marginBottom: 24,
  },
  greeting:  { fontSize: 20, fontWeight: '700', color: '#fff' },
  date:      { fontSize: 13, color: COLORS.textMuted, marginTop: 2 },
  headerActions: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  bellBtn: { padding: 8, backgroundColor: COLORS.card, borderRadius: 10, borderWidth: 1, borderColor: COLORS.border },
  badge: { position: 'absolute', top: -4, right: -4, backgroundColor: '#ef4444', borderRadius: 8, minWidth: 16, height: 16, justifyContent: 'center', alignItems: 'center', paddingHorizontal: 3 },
  badgeText: { color: '#fff', fontSize: 9, fontWeight: '700' },
  logoutBtn: { padding: 8, backgroundColor: COLORS.card, borderRadius: 10, borderWidth: 1, borderColor: COLORS.border },
=======
    container:{
>>>>>>> 0ed281a (Redesign employee dashboard with professional SaaS UI)

        flex:1,

    },

    loadingContainer:{

        flex:1,

        justifyContent:"center",

        alignItems:"center",

    },

    content:{

        paddingHorizontal:20,

        paddingTop:55,

        paddingBottom:110,

    },

});