import React from "react";

import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
} from "react-native";

import LEAVE_THEME from "../../constants/leaveTheme";

const TABS = [
  {
    key: "requests",
    title: "Requests",
  },
  {
    key: "holidays",
    title: "Holidays",
  },
  {
    key: "tickets",
    title: "Tickets",
  },
  {
    key: "resignations",
    title: "Resign",
  },
];

export default function LeaveSegmentTabs({
  selectedTab,
  onTabChange,
}) {
  return (
    <View style={styles.container}>

      {TABS.map((tab) => {

        const active =
          selectedTab === tab.key;

        return (

          <TouchableOpacity
            key={tab.key}
            activeOpacity={0.85}
            style={[
              styles.tab,
              active &&
                styles.activeTab,
            ]}
            onPress={() =>
              onTabChange(tab.key)
            }
          >

            <Text
              style={[
                styles.tabText,
                active &&
                  styles.activeTabText,
              ]}
            >
              {tab.title}
            </Text>

          </TouchableOpacity>

        );

      })}

    </View>
  );
}

const styles = StyleSheet.create({

  container: {
    flexDirection: "row",

    backgroundColor: "#EEF2F7",

    borderRadius: 18,

    padding: 4,

    marginBottom: 20,
  },

  tab: {
    flex: 1,

    height: 46,

    borderRadius: 14,

    justifyContent: "center",

    alignItems: "center",
  },

  activeTab: {
    backgroundColor: "#FFFFFF",

    shadowColor: "#000",

    shadowOpacity: 0.06,

    shadowRadius: 8,

    shadowOffset: {
      width: 0,
      height: 4,
    },

    elevation: 3,
  },

  tabText: {
    fontSize: 13,

    fontWeight: "700",

    color:
      LEAVE_THEME.colors.textMuted,
  },

  activeTabText: {
    color:
      LEAVE_THEME.colors.primary,
  },

});