import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  Pressable,
} from 'react-native';

import { Ionicons } from '@expo/vector-icons';
import AppCard from '../ui/AppCard';

const CONFIG = {

  employees: {
    icon: 'people',
    iconColor: '#2563EB',
    background: '#EEF4FF',
  },

  present: {
    icon: 'checkmark-circle',
    iconColor: '#16A34A',
    background: '#ECFDF3',
  },

  absent: {
    icon: 'close-circle',
    iconColor: '#DC2626',
    background: '#FEF2F2',
  },

  late: {
    icon: 'time',
    iconColor: '#D97706',
    background: '#FFF7E6',
  },

};

export default function StatCard({

  title,
  value,
  type = "employees",
  trend = "+2.4%",
  trendType = "positive",
  onPress,

}) {

  const item = CONFIG[type];

  return (

    <Pressable

      onPress={onPress}

      style={({ pressed }) => [

        styles.wrapper,

        pressed && styles.pressed,

      ]}

    >

      <AppCard style={styles.card}>

        <View style={styles.header}>

          <View
            style={[
              styles.iconBox,
              {
                backgroundColor: item.background,
              },
            ]}
          >

            <Ionicons

              name={item.icon}

              size={20}

              color={item.iconColor}

            />

          </View>

          <Ionicons

            name="trending-up-outline"

            size={15}

            color="#CBD5E1"

          />

        </View>

        <Text style={styles.value}>
          {value}
        </Text>

        <Text style={styles.title}>
          {title}
        </Text>

        <View style={styles.footer}>

          <Ionicons

            name={
              trendType === "positive"
                ? "arrow-up"
                : "arrow-down"
            }

            size={11}

            color={
              trendType === "positive"
                ? "#16A34A"
                : "#DC2626"
            }

          />

          <Text

            style={[
              styles.trend,

              {

                color:
                  trendType === "positive"
                    ? "#16A34A"
                    : "#DC2626",

              },

            ]}

          >

            {trend}

          </Text>

          <Text style={styles.period}>

            vs yesterday

          </Text>

        </View>

      </AppCard>

    </Pressable>

  );

}

const styles = StyleSheet.create({

  wrapper: {

    flex: 1,

  },

  pressed: {

    opacity: 0.9,

    transform: [
      {
        scale: 0.985,
      },
    ],

  },

  card: {

    minHeight: 122,

    padding: 18,

    borderRadius: 22,

  },

  header: {

    flexDirection: "row",

    justifyContent: "space-between",

    alignItems: "center",

  },

  iconBox: {

    width: 42,

    height: 42,

    borderRadius: 14,

    justifyContent: "center",

    alignItems: "center",

  },

  value: {

    marginTop: 18,

    fontSize: 33,

    fontWeight: "800",

    color: "#0F172A",

    letterSpacing: -1,

  },

  title: {

    marginTop: 4,

    fontSize: 13,

    color: "#64748B",

    fontWeight: "600",

  },

  footer: {

    flexDirection: "row",

    alignItems: "center",

    marginTop: 14,

  },

  trend: {

    marginLeft: 4,

    fontWeight: "700",

    fontSize: 11,

  },

  period: {

    marginLeft: 6,

    fontSize: 11,

    color: "#94A3B8",

  },

});