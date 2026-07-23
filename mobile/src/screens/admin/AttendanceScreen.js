import React, { useState } from "react";
import {
  SafeAreaView,
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  FlatList,
} from "react-native";
import { DrawerActions } from "@react-navigation/native";
import { Ionicons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";

import AdminHeader from "../../components/admin/AdminHeader";

export default function AttendanceScreen({ navigation }) {
  const [search, setSearch] = useState("");
  const [month, setMonth] = useState("July");
  const [year, setYear] = useState("2026");

  const summary = {
    employees: 254,
    workingDays: 26,
    attendance: 92,
    holidays: 2,
  };

  const employees = [
    {
      id: "EMP001",
      name: "John Anderson",
      full: 22,
      late: 2,
      half: 1,
      absent: 1,
      working: 26,
      percent: 92,
    },
    {
      id: "EMP002",
      name: "Sophia Brown",
      full: 24,
      late: 1,
      half: 0,
      absent: 1,
      working: 26,
      percent: 96,
    },
    {
      id: "EMP003",
      name: "Michael Wilson",
      full: 20,
      late: 3,
      half: 2,
      absent: 1,
      working: 26,
      percent: 86,
    },
    {
      id: "EMP004",
      name: "Emma Davis",
      full: 25,
      late: 0,
      half: 0,
      absent: 1,
      working: 26,
      percent: 98,
    },
  ];

  const renderEmployee = ({ item }) => (
    <View style={styles.employeeCard}>
      <View style={styles.employeeHeader}>
        <View>
          <Text style={styles.employeeName}>{item.name}</Text>
          <Text style={styles.employeeId}>{item.id}</Text>
        </View>

        <View style={styles.percentBadge}>
          <Text style={styles.percentText}>{item.percent}%</Text>
        </View>
      </View>

      <View style={styles.progressBackground}>
        <View
          style={[
            styles.progressFill,
            {
              width: `${item.percent}%`,
            },
          ]}
        />
      </View>

      <View style={styles.statsRow}>
        <View style={styles.statChipGreen}>
          <Text style={styles.chipValue}>{item.full}</Text>
          <Text style={styles.chipLabel}>Full</Text>
        </View>

        <View style={styles.statChipOrange}>
          <Text style={styles.chipValue}>{item.late}</Text>
          <Text style={styles.chipLabel}>Late</Text>
        </View>

        <View style={styles.statChipBlue}>
          <Text style={styles.chipValue}>{item.half}</Text>
          <Text style={styles.chipLabel}>Half</Text>
        </View>

        <View style={styles.statChipRed}>
          <Text style={styles.chipValue}>{item.absent}</Text>
          <Text style={styles.chipLabel}>Absent</Text>
        </View>
      </View>
    </View>
  );

  return (
    <LinearGradient
      colors={["#F8FAFC", "#F3F7FD", "#EDF4FF"]}
      style={styles.container}
    >
      <SafeAreaView style={{ flex: 1 }}>
        <AdminHeader
          title="Attendance"
          onMenu={() =>
            navigation.dispatch(DrawerActions.openDrawer())
          }
        />

        <ScrollView
          showsVerticalScrollIndicator={false}
          contentContainerStyle={styles.content}
        >
          <View style={styles.searchContainer}>
            <Ionicons
              name="search"
              size={20}
              color="#94A3B8"
            />

            <TextInput
              placeholder="Search employee..."
              placeholderTextColor="#94A3B8"
              value={search}
              onChangeText={setSearch}
              style={styles.searchInput}
            />
          </View>

          <View style={styles.filterRow}>
            <TouchableOpacity style={styles.dropdown}>
              <Text style={styles.dropdownText}>{month}</Text>
              <Ionicons
                name="chevron-down"
                size={18}
                color="#64748B"
              />
            </TouchableOpacity>

            <TouchableOpacity style={styles.dropdown}>
              <Text style={styles.dropdownText}>{year}</Text>
              <Ionicons
                name="chevron-down"
                size={18}
                color="#64748B"
              />
            </TouchableOpacity>
          </View>

          <View style={styles.buttonRow}>
            <TouchableOpacity style={styles.primaryButton}>
              <Ionicons
                name="bar-chart"
                size={18}
                color="#FFFFFF"
              />

              <Text style={styles.primaryText}>
                View Report
              </Text>
            </TouchableOpacity>

            <TouchableOpacity style={styles.successButton}>
              <Ionicons
                name="download"
                size={18}
                color="#FFFFFF"
              />

              <Text style={styles.primaryText}>
                Download
              </Text>
            </TouchableOpacity>
          </View>

          <View style={styles.summaryGrid}>
            <View style={styles.summaryCard}>
              <Ionicons
                name="people"
                size={26}
                color="#2563EB"
              />
              <Text style={styles.summaryValue}>
                {summary.employees}
              </Text>
              <Text style={styles.summaryLabel}>
                Employees
              </Text>
            </View>

            <View style={styles.summaryCard}>
              <Ionicons
                name="calendar"
                size={26}
                color="#16A34A"
              />
              <Text style={styles.summaryValue}>
                {summary.workingDays}
              </Text>
              <Text style={styles.summaryLabel}>
                Working Days
              </Text>
            </View>

            <View style={styles.summaryCard}>
              <Ionicons
                name="checkmark-circle"
                size={26}
                color="#F59E0B"
              />
              <Text style={styles.summaryValue}>
                {summary.attendance}%
              </Text>
              <Text style={styles.summaryLabel}>
                Attendance
              </Text>
            </View>

            <View style={styles.summaryCard}>
              <Ionicons
                name="gift"
                size={26}
                color="#EF4444"
              />
              <Text style={styles.summaryValue}>
                {summary.holidays}
              </Text>
              <Text style={styles.summaryLabel}>
                Holidays
              </Text>
            </View>
          </View>

          <Text style={styles.sectionTitle}>
            Employee Attendance
          </Text>

          <FlatList
            data={employees}
            keyExtractor={(item) => item.id}
            renderItem={renderEmployee}
            scrollEnabled={false}
          />

          <View style={{ height: 120 }} />
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

  searchContainer: {
    marginTop: 16,

    height: 56,

    backgroundColor: "#FFFFFF",

    borderRadius: 18,

    paddingHorizontal: 18,

    flexDirection: "row",

    alignItems: "center",

    shadowColor: "#000",

    shadowOpacity: 0.05,

    shadowRadius: 12,

    shadowOffset: {
      width: 0,
      height: 5,
    },

    elevation: 4,
  },

  searchInput: {
    flex: 1,

    marginLeft: 12,

    fontSize: 15,

    color: "#0F172A",

    fontWeight: "500",
  },

  filterRow: {
    flexDirection: "row",

    justifyContent: "space-between",

    marginTop: 20,
  },

  dropdown: {
    width: "48%",

    height: 52,

    backgroundColor: "#FFFFFF",

    borderRadius: 16,

    borderWidth: 1,

    borderColor: "#E2E8F0",

    flexDirection: "row",

    justifyContent: "space-between",

    alignItems: "center",

    paddingHorizontal: 16,
  },

  dropdownText: {
    fontSize: 15,

    color: "#1E293B",

    fontWeight: "600",
  },

  buttonRow: {
    flexDirection: "row",

    justifyContent: "space-between",

    marginTop: 18,

    marginBottom: 24,
  },

  primaryButton: {
    width: "48%",

    height: 52,

    borderRadius: 16,

    backgroundColor: "#2563EB",

    flexDirection: "row",

    justifyContent: "center",

    alignItems: "center",
  },

  successButton: {
    width: "48%",

    height: 52,

    borderRadius: 16,

    backgroundColor: "#22C55E",

    flexDirection: "row",

    justifyContent: "center",

    alignItems: "center",
  },

  primaryText: {
    color: "#FFFFFF",

    fontWeight: "700",

    fontSize: 15,

    marginLeft: 8,
  },

  summaryGrid: {
    flexDirection: "row",

    flexWrap: "wrap",

    justifyContent: "space-between",

    marginBottom: 28,
  },

  summaryCard: {
    width: "48%",

    backgroundColor: "#FFFFFF",

    borderRadius: 20,

    paddingVertical: 22,

    alignItems: "center",

    marginBottom: 16,

    borderWidth: 1,

    borderColor: "#E5E7EB",

    shadowColor: "#000",

    shadowOpacity: 0.05,

    shadowRadius: 10,

    shadowOffset: {
      width: 0,
      height: 5,
    },

    elevation: 4,
  },

  summaryValue: {
    marginTop: 12,

    fontSize: 28,

    fontWeight: "800",

    color: "#0F172A",
  },

  summaryLabel: {
    marginTop: 6,

    fontSize: 13,

    color: "#64748B",

    fontWeight: "600",
  },

  sectionTitle: {
    fontSize: 22,

    fontWeight: "800",

    color: "#0F172A",

    marginBottom: 18,
  },

  employeeCard: {
    backgroundColor: "#FFFFFF",

    borderRadius: 22,

    padding: 20,

    marginBottom: 18,

    borderWidth: 1,

    borderColor: "#E5E7EB",

    shadowColor: "#000",

    shadowOpacity: 0.05,

    shadowRadius: 10,

    shadowOffset: {
      width: 0,
      height: 5,
    },

    elevation: 4,
  },
    employeeHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 16,
  },

  employeeName: {
    fontSize: 17,
    fontWeight: "700",
    color: "#0F172A",
  },

  employeeId: {
    marginTop: 4,
    fontSize: 13,
    color: "#64748B",
    fontWeight: "500",
  },

  percentBadge: {
    minWidth: 64,
    height: 36,
    borderRadius: 18,
    backgroundColor: "#DBEAFE",
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 12,
  },

  percentText: {
    color: "#2563EB",
    fontWeight: "800",
    fontSize: 15,
  },

  progressBackground: {
    width: "100%",
    height: 10,
    borderRadius: 6,
    backgroundColor: "#E2E8F0",
    overflow: "hidden",
    marginBottom: 18,
  },

  progressFill: {
    height: "100%",
    borderRadius: 6,
    backgroundColor: "#22C55E",
  },

  statsRow: {
    flexDirection: "row",
    justifyContent: "space-between",
  },

  statChipGreen: {
    width: "23%",
    borderRadius: 14,
    backgroundColor: "#ECFDF5",
    alignItems: "center",
    paddingVertical: 12,
  },

  statChipOrange: {
    width: "23%",
    borderRadius: 14,
    backgroundColor: "#FFF7ED",
    alignItems: "center",
    paddingVertical: 12,
  },

  statChipBlue: {
    width: "23%",
    borderRadius: 14,
    backgroundColor: "#EFF6FF",
    alignItems: "center",
    paddingVertical: 12,
  },

  statChipRed: {
    width: "23%",
    borderRadius: 14,
    backgroundColor: "#FEF2F2",
    alignItems: "center",
    paddingVertical: 12,
  },

  chipValue: {
    fontSize: 18,
    fontWeight: "800",
    color: "#0F172A",
  },

  chipLabel: {
    marginTop: 4,
    fontSize: 12,
    color: "#64748B",
    fontWeight: "600",
  },
});