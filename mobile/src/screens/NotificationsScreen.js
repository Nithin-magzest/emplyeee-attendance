import React, { useMemo, useState } from "react";
import {
  SafeAreaView,
  ScrollView,
  StyleSheet,
  RefreshControl,
  Alert,
} from "react-native";

import ProfileHeader from "../components/profile/ProfileHeader";

import NotificationHeaderCard from "../components/notifications/NotificationHeaderCard";
import NotificationFilter from "../components/notifications/NotificationFilter";
import NotificationCard from "../components/notifications/NotificationCard";
import NotificationEmpty from "../components/notifications/NotificationEmpty";

import {
  notifications,
  notificationFilters,
} from "../data/notificationsData";

export default function NotificationsScreen() {
  const [selectedFilter, setSelectedFilter] =
    useState("All");

  const [refreshing, setRefreshing] =
    useState(false);

  const filteredNotifications = useMemo(() => {
    switch (selectedFilter) {
      case "Unread":
        return notifications.filter(
          (item) => item.unread
        );

      case "HR":
        return notifications.filter(
          (item) => item.type === "HR"
        );

      case "Attendance":
        return notifications.filter(
          (item) =>
            item.type === "Attendance"
        );

      case "Leave":
        return notifications.filter(
          (item) => item.type === "Leave"
        );

      default:
        return notifications;
    }
  }, [selectedFilter]);

  const unreadCount =
    notifications.filter(
      (item) => item.unread
    ).length;

  const onRefresh = () => {
    setRefreshing(true);

    setTimeout(() => {
      setRefreshing(false);
    }, 1000);
  };

  const handleNotificationPress = (
    notification
  ) => {
    Alert.alert(
      notification.title,
      notification.message
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <ProfileHeader
        title="Alerts"
        showBack={false}
      />

      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            colors={["#173B8C"]}
            tintColor="#173B8C"
          />
        }
      >
        <NotificationHeaderCard
          total={notifications.length}
          unread={unreadCount}
        />

        <NotificationFilter
          filters={notificationFilters}
          selectedFilter={
            selectedFilter
          }
          onSelectFilter={
            setSelectedFilter
          }
        />

        {filteredNotifications.length >
        0 ? (
          filteredNotifications.map(
            (notification) => (
              <NotificationCard
                key={notification.id}
                notification={
                  notification
                }
                onPress={
                  handleNotificationPress
                }
              />
            )
          )
        ) : (
          <NotificationEmpty />
        )}

              <SafeAreaView
        style={{
          height: 110,
        }}
      />
    </ScrollView>
  </SafeAreaView>
);
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F5F7FB",
  },

  content: {
    paddingHorizontal: 20,
    paddingTop: 18,
    paddingBottom: 30,
  },
});
