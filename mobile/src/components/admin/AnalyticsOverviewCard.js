import React from "react";
import {
  View,
  Text,
  StyleSheet,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

const DATA = [
  {
    title: "Productivity",
    value: "94%",
    icon: "trending-up",
    color: "#16A34A",
    background: "#DCFCE7",
  },
  {
    title: "Performance",
    value: "A+",
    icon: "ribbon",
    color: "#2563EB",
    background: "#DBEAFE",
  },
  {
    title: "Attrition",
    value: "3%",
    icon: "people",
    color: "#F59E0B",
    background: "#FEF3C7",
  },
];

export default function AnalyticsOverviewCard() {
  return (
    <View style={styles.container}>

      <Text style={styles.heading}>
        Analytics Overview
      </Text>

      <View style={styles.row}>

        {DATA.map((item) => (

          <View
            key={item.title}
            style={styles.card}
          >

            <View
              style={[
                styles.iconContainer,
                {
                  backgroundColor:
                    item.background,
                },
              ]}
            >

              <Ionicons
                name={item.icon}
                size={24}
                color={item.color}
              />

            </View>

            <Text style={styles.value}>
              {item.value}
            </Text>

            <Text style={styles.label}>
              {item.title}
            </Text>

          </View>

        ))}

      </View>

    </View>
  );
}

const styles = StyleSheet.create({

  container: {
    marginBottom: 28,
  },

  heading: {
    fontSize: 22,
    fontWeight: "800",
    color: "#0F172A",
    marginBottom: 18,
  },

  row: {
    flexDirection: "row",
    justifyContent: "space-between",
  },

  card: {
    width: "31%",

    backgroundColor: "#FFFFFF",

    borderRadius: 22,

    paddingVertical: 18,

    alignItems: "center",

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
    marginBottom: 14,
  },

  value: {
    fontSize: 24,
    fontWeight: "800",
    color: "#0F172A",
  },

  label: {
    marginTop: 6,
    fontSize: 12,
    color: "#64748B",
    fontWeight: "600",
  },

});