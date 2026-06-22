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

export default function AdminDashboard() {

    const { signOut } = useAuth();

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

    const handleLogout = async () => {
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
            colors={["#F6F9FF", "#EDF4FF", "#E8F0FF"]}
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

                {data?.today_rows?.length > 0
                    ? data.today_rows.map(employee => (
                        <AttendanceCard
                            key={employee.employee_id}
                            employee={employee}
                        />
                    ))
                    : <EmptyState
                        icon="people-outline"
                        title="No Attendance"
                        subtitle="No employees have checked in today."
                    />
                }

                <DashboardActivity />

                <View style={{ height: 40 }} />

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
    },
    content: {
        paddingHorizontal: 20,
        paddingTop: 55,
        paddingBottom: 110,
    },
});
