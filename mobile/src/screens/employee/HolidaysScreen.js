import React, { useState } from "react";
import {
  SafeAreaView,
  ScrollView,
  View,
  Text,
} from "react-native";

import { StyleSheet } from "react-native";

import ProfileHeader from "../../components/profile/ProfileHeader";

import HolidayHeaderCard from "../../components/holidays/HolidayHeaderCard";
import HolidaySummaryCard from "../../components/holidays/HolidaySummaryCard";
import YearSelector from "../../components/holidays/YearSelector";
import HolidayLegend from "../../components/holidays/HolidayLegend";
import HolidayCalendar from "../../components/holidays/HolidayCalendar";
import HolidayList from "../../components/holidays/HolidayList";
import EmptyHolidayCard from "../../components/holidays/EmptyHolidayCard";

export default function HolidaysScreen() {
  const [year, setYear] = useState(2026);

  const [selectedDate, setSelectedDate] =
    useState(null);

  const holidays = [
    {
      id: 1,
      day: 1,
      title: "New Year's Day",
      date: "1 January 2026",
      type: "Public",
      description:
        "Celebration of the New Year.",
    },
    {
      id: 2,
      day: 14,
      title: "Makar Sankranti",
      date: "14 January 2026",
      type: "Optional",
      description:
        "Harvest festival celebrated across India.",
    },
    {
      id: 3,
      day: 26,
      title: "Republic Day",
      date: "26 January 2026",
      type: "Public",
      description:
        "National holiday commemorating the Constitution.",
    },
    {
      id: 4,
      day: 15,
      title: "Independence Day",
      date: "15 August 2026",
      type: "Public",
      description:
        "National Independence Day celebration.",
    },
    {
      id: 5,
      day: 2,
      title: "Gandhi Jayanti",
      date: "2 October 2026",
      type: "Public",
      description:
        "Birth anniversary of Mahatma Gandhi.",
    },
    {
      id: 6,
      day: 25,
      title: "Christmas",
      date: "25 December 2026",
      type: "Company",
      description:
        "Christmas Holiday.",
    },
  ];

  return (
    <SafeAreaView style={styles.container}>
      <ProfileHeader
        title="Holiday Calendar"
        showBack={false}
      />

      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.content}
      >
        {/* Header */}

        <HolidayHeaderCard
          year={year}
          totalHolidays={18}
          publicHolidays={12}
          optionalHolidays={4}
          companyHolidays={2}
        />

        {/* Upcoming */}

        <HolidaySummaryCard
          upcomingHoliday="Independence Day"
          holidayDate="15 August 2026"
          remainingDays={46}
          holidayType="Public Holiday"
        />

        {/* Year */}

        <YearSelector
          year={year}
          onPrevious={() =>
            setYear(year - 1)
          }
          onNext={() =>
            setYear(year + 1)
          }
        />

        {/* Legend */}

        <HolidayLegend />

        {/* Calendar */}

        <HolidayCalendar
          month={5}
          year={year}
          holidays={holidays}
          selectedDate={selectedDate}
          onDatePress={(day) =>
            setSelectedDate(day)
          }
        />

        {/* Holiday List */}

        <Text style={styles.sectionTitle}>
          Holidays
        </Text>

        {holidays.length > 0 ? (
          <HolidayList
            holidays={holidays}
          />
        ) : (
          <EmptyHolidayCard />
        )}

        <View
          style={{
            height: 40,
          }}
        />
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
    marginTop: 26,
    marginBottom: 16,

    fontSize: 22,

    fontWeight: "800",

    color: "#0F172A",

    letterSpacing: -0.5,
  },

  card: {
    backgroundColor: "#FFFFFF",

    borderRadius: 22,

    padding: 20,

    marginBottom: 18,

    borderWidth: 1,

    borderColor: "#E8EDF3",

    shadowColor: "#0F172A",
    shadowOpacity: 0.05,
    shadowRadius: 10,
    shadowOffset: {
      width: 0,
      height: 5,
    },

    elevation: 3,
  },

  row: {
    flexDirection: "row",

    justifyContent: "space-between",

    alignItems: "center",

    paddingVertical: 12,

    borderBottomWidth: 1,

    borderBottomColor: "#EEF2F7",
  },

  rowLeft: {
    flexDirection: "row",

    alignItems: "center",

    flex: 1,
  },

  rowRight: {
    alignItems: "flex-end",
  },

  iconContainer: {
    width: 42,
    height: 42,

    borderRadius: 14,

    backgroundColor: "#EEF4FF",

    justifyContent: "center",
    alignItems: "center",

    marginRight: 14,
  },

  title: {
    fontSize: 16,

    fontWeight: "700",

    color: "#0F172A",
  },

  subtitle: {
    marginTop: 3,

    fontSize: 13,

    color: "#64748B",
  },

  value: {
    fontSize: 16,

    fontWeight: "800",

    color: "#173B8C",
  },

  badge: {
    marginTop: 6,

    paddingHorizontal: 12,

    paddingVertical: 5,

    borderRadius: 16,

    backgroundColor: "#EEF4FF",
  },

  badgeText: {
    color: "#173B8C",

    fontWeight: "700",

    fontSize: 12,
  },

  infoCard: {
    marginTop: 20,

    backgroundColor: "#EEF4FF",

    borderLeftWidth: 4,

    borderLeftColor: "#173B8C",

    borderRadius: 18,

    padding: 18,
  },

  infoTitle: {
    fontSize: 16,

    fontWeight: "800",

    color: "#173B8C",

    marginBottom: 8,
  },

  infoText: {
    color: "#475569",

    fontSize: 14,

    lineHeight: 22,

    fontWeight: "500",
  },

  divider: {
    height: 1,

    backgroundColor: "#EEF2F7",

    marginVertical: 20,
  },

  footerCard: {
    marginTop: 20,

    backgroundColor: "#FFFFFF",

    borderRadius: 22,

    padding: 20,

    borderWidth: 1,

    borderColor: "#E8EDF3",

    shadowColor: "#0F172A",
    shadowOpacity: 0.05,
    shadowRadius: 10,
    shadowOffset: {
      width: 0,
      height: 5,
    },

    elevation: 3,
  },

  footerTitle: {
    fontSize: 18,

    fontWeight: "800",

    color: "#0F172A",

    marginBottom: 10,
  },

  footerText: {
    fontSize: 14,

    lineHeight: 22,

    color: "#64748B",
  },

  statsRow: {
    flexDirection: "row",

    justifyContent: "space-between",

    marginTop: 18,
  },

  statBox: {
    flex: 1,

    backgroundColor: "#FFFFFF",

    borderRadius: 18,

    paddingVertical: 16,

    alignItems: "center",

    marginHorizontal: 4,

    borderWidth: 1,

    borderColor: "#E8EDF3",

    shadowColor: "#0F172A",
    shadowOpacity: 0.03,
    shadowRadius: 8,
    shadowOffset: {
      width: 0,
      height: 3,
    },

    elevation: 2,
  },

  statNumber: {
    marginTop: 6,

    fontSize: 24,

    fontWeight: "800",

    color: "#173B8C",
  },

  statLabel: {
    marginTop: 4,

    fontSize: 12,

    color: "#64748B",

    fontWeight: "600",

    textAlign: "center",
  },
});