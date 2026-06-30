import React from "react";
import {
  SafeAreaView,
  ScrollView,
  View,
  Text,
} from "react-native";

import { StyleSheet } from "react-native";

import ProfileHeader from "../../components/profile/ProfileHeader";

import EmployeePerformanceCard from "../../components/performance/EmployeePerformanceCard";
import RatingCard from "../../components/performance/RatingCard";
import MetricCard from "../../components/performance/MetricCard";
import PerformanceTimeline from "../../components/performance/PerformanceTimeline";
import AchievementCard from "../../components/performance/AchievementCard";
import ManagerRemarksCard from "../../components/performance/ManagerRemarksCard";
import UpcomingReviewCard from "../../components/performance/UpcomingReviewCard";

export default function PerformanceScreen() {
  const employee = {
    name: "John Doe",
    employeeId: "EMP001",
    designation: "Software Engineer",
    department: "Engineering",
  };

  const performance = {
    rating: 4,
    score: 88,
    quarter: "Q2 - 2026",
    status: "Completed",
  };

  const metrics = [
    {
      title: "Productivity",
      icon: "trending-up-outline",
      score: 92,
      color: "#22C55E",
      background: "#ECFDF5",
    },
    {
      title: "Attendance",
      icon: "calendar-outline",
      score: 88,
      color: "#2563EB",
      background: "#EEF4FF",
    },
    {
      title: "Teamwork",
      icon: "people-outline",
      score: 95,
      color: "#8B5CF6",
      background: "#F3E8FF",
    },
    {
      title: "Innovation",
      icon: "bulb-outline",
      score: 82,
      color: "#F59E0B",
      background: "#FFF7ED",
    },
    {
      title: "Goal Completion",
      icon: "flag-outline",
      score: 90,
      color: "#06B6D4",
      background: "#ECFEFF",
    },
  ];

  const timeline = [
    {
      quarter: "Q1",
      year: "2025",
      score: 81,
    },
    {
      quarter: "Q2",
      year: "2025",
      score: 84,
    },
    {
      quarter: "Q3",
      year: "2025",
      score: 87,
    },
    {
      quarter: "Q4",
      year: "2025",
      score: 89,
    },
    {
      quarter: "Q1",
      year: "2026",
      score: 91,
    },
    {
      quarter: "Q2",
      year: "2026",
      score: 88,
    },
  ];

  return (
    <SafeAreaView style={styles.container}>
      <ProfileHeader
        title="My Performance"
        showBack={false}
      />

      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.content}
      >
        <EmployeePerformanceCard
          name={employee.name}
          designation={employee.designation}
          department={employee.department}
          employeeId={employee.employeeId}
        />

        <RatingCard
          rating={performance.rating}
          score={performance.score}
          quarter={performance.quarter}
          status={performance.status}
        />

        <Text style={styles.sectionTitle}>
          Performance Metrics
        </Text>

        {metrics.map((metric) => (
          <MetricCard
            key={metric.title}
            title={metric.title}
            icon={metric.icon}
            score={metric.score}
            color={metric.color}
            background={metric.background}
          />
        ))}

        <Text style={styles.sectionTitle}>
          Achievements
        </Text>

        <AchievementCard
          title="Employee of the Month"
          subtitle="Recognized for exceptional contribution and ownership."
          icon="trophy"
          color="#F59E0B"
          background="#FFF7ED"
        />

        <AchievementCard
          title="Perfect Attendance"
          subtitle="Maintained outstanding attendance this quarter."
          icon="calendar"
          color="#22C55E"
          background="#ECFDF5"
        />

        <AchievementCard
          title="Team Excellence"
          subtitle="Awarded for outstanding collaboration."
          icon="people"
          color="#2563EB"
          background="#EEF4FF"
        />

        <Text style={styles.sectionTitle}>
          Performance History
        </Text>

        <PerformanceTimeline
          timeline={timeline}
        />

        <Text style={styles.sectionTitle}>
          Manager Feedback
        </Text>

        <ManagerRemarksCard
          managerName="Michael Smith"
          designation="Engineering Manager"
          remarks="Excellent performance throughout the quarter. You consistently deliver high-quality work, collaborate effectively with the team, and take ownership of critical tasks. Continue improving leadership skills and mentoring junior developers."
        />

        <Text style={styles.sectionTitle}>
          Upcoming Review
        </Text>

        <UpcomingReviewCard
          reviewDate="15 July 2026"
          reviewType="Quarterly Performance Review"
          reviewer="Michael Smith"
          status="Scheduled"
          onPress={() => {
            console.log("View Review");
          }}
        />

        <View style={{ height: 40 }} />
      </ScrollView>
    </SafeAreaView>
  );
}
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F8FAFC",
  },

  content: {
    paddingHorizontal: 18,
    paddingBottom: 120,
  },

  sectionTitle: {
    marginTop: 22,
    marginBottom: 14,

    fontSize: 20,
    fontWeight: "800",

    color: "#0F172A",

    letterSpacing: -0.4,
  },

  card: {
    backgroundColor: "#FFFFFF",

    borderRadius: 22,

    padding: 18,

    marginBottom: 18,

    borderWidth: 1,
    borderColor: "#E8EDF3",

    shadowColor: "#0F172A",
    shadowOpacity: 0.04,
    shadowRadius: 10,
    shadowOffset: {
      width: 0,
      height: 5,
    },

    elevation: 2,
  },

  cardHeader: {
    flexDirection: "row",
    alignItems: "center",

    marginBottom: 16,
  },

  cardTitle: {
    marginLeft: 10,

    fontSize: 18,
    fontWeight: "800",

    color: "#0F172A",
  },

  divider: {
    height: 1,
    backgroundColor: "#EEF2F7",
    marginVertical: 16,
  },

  infoRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",

    paddingVertical: 10,
  },

  infoLabel: {
    fontSize: 15,
    fontWeight: "600",
    color: "#64748B",
  },

  infoValue: {
    fontSize: 15,
    fontWeight: "800",
    color: "#173B8C",
  },

  badge: {
    alignSelf: "flex-start",

    paddingHorizontal: 14,
    paddingVertical: 6,

    borderRadius: 30,

    backgroundColor: "#EEF4FF",

    marginTop: 8,
  },

  badgeText: {
    color: "#173B8C",
    fontWeight: "700",
    fontSize: 13,
  },

  noteCard: {
    marginTop: 20,

    padding: 16,

    borderRadius: 18,

    backgroundColor: "#EEF4FF",

    borderLeftWidth: 4,
    borderLeftColor: "#173B8C",
  },

  noteTitle: {
    fontSize: 16,
    fontWeight: "800",
    color: "#173B8C",

    marginBottom: 8,
  },

  noteText: {
    fontSize: 14,
    lineHeight: 22,
    color: "#475569",
    fontWeight: "500",
  },

  footerSpacing: {
    height: 40,
  },
});