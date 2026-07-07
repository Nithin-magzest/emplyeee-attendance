import React from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

import THEME from "../../constants/theme";

const DEFAULT_ANNOUNCEMENTS = [
  {
    id: 1,
    title: "Company Meeting",
    message:
      "Monthly all-hands meeting scheduled tomorrow at 10:00 AM.",
    date: "Tomorrow",
    type: "meeting",
  },
  {
    id: 2,
    title: "Holiday Notice",
    message:
      "Office will remain closed on Independence Day.",
    date: "15 Aug",
    type: "holiday",
  },
  {
    id: 3,
    title: "Payroll Update",
    message:
      "Salary will be credited on the last working day.",
    date: "This Month",
    type: "payroll",
  },
];

function getIcon(type) {
  switch (type) {
    case "holiday":
      return {
        icon: "airplane",
        color: "#2563EB",
        bg: "#DBEAFE",
      };

    case "meeting":
      return {
        icon: "people",
        color: "#16A34A",
        bg: "#DCFCE7",
      };

    case "payroll":
      return {
        icon: "wallet",
        color: "#7C3AED",
        bg: "#EDE9FE",
      };

    default:
      return {
        icon: "notifications",
        color: "#F59E0B",
        bg: "#FEF3C7",
      };
  }
}

export default function AnnouncementCard({

  announcements = DEFAULT_ANNOUNCEMENTS,

  onViewAll = () => {},

}) {

  return (

    <View style={styles.container}>

      <View style={styles.header}>

        <Text style={styles.heading}>
          Announcements
        </Text>

        <TouchableOpacity
          onPress={onViewAll}
          activeOpacity={0.8}
        >
          <Text style={styles.viewAll}>
            View All
          </Text>
        </TouchableOpacity>

      </View>

      {announcements.map((item) => {

        const config = getIcon(item.type);

        return (

          <View
            key={item.id}
            style={styles.card}
          >

            <View
              style={[
                styles.iconContainer,
                {
                  backgroundColor:
                    config.bg,
                },
              ]}
            >

              <Ionicons
                name={config.icon}
                size={22}
                color={config.color}
              />

            </View>

            <View style={styles.content}>

              <Text style={styles.title}>
                {item.title}
              </Text>

              <Text
                numberOfLines={2}
                style={styles.message}
              >
                {item.message}
              </Text>

            </View>

            <Text style={styles.date}>
              {item.date}
            </Text>

          </View>

        );

      })}

    </View>

  );

}

const styles = StyleSheet.create({

  container: {

    marginBottom: 28,

  },

  header: {

    flexDirection: "row",

    justifyContent: "space-between",

    alignItems: "center",

    marginBottom: 18,

  },

  heading: {

    fontSize: 22,

    fontWeight: "800",

    color: "#0F172A",

  },

  viewAll: {

    color: THEME.colors.primary,

    fontWeight: "700",

    fontSize: 14,

  },

  card: {

    flexDirection: "row",

    alignItems: "center",

    backgroundColor: "#FFFFFF",

    borderRadius: 22,

    padding: 16,

    marginBottom: 14,

    borderWidth: 1,

    borderColor: "#E8EDF5",

    shadowColor: "#000",

    shadowOpacity: 0.05,

    shadowRadius: 10,

    shadowOffset: {

      width: 0,

      height: 5,

    },

    elevation: 4,

  },

  iconContainer: {

    width: 54,

    height: 54,

    borderRadius: 18,

    justifyContent: "center",

    alignItems: "center",

  },

  content: {

    flex: 1,

    marginLeft: 16,

  },

  title: {

    fontSize: 15,

    fontWeight: "700",

    color: "#0F172A",

  },

  message: {

    marginTop: 5,

    fontSize: 13,

    color: "#64748B",

    lineHeight: 18,

  },

  date: {

    marginLeft: 10,

    fontSize: 12,

    color: "#94A3B8",

    fontWeight: "600",

  },

});