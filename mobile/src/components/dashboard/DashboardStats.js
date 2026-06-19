import React from 'react';
import { View, StyleSheet } from 'react-native';
import StatCard from './StatCard';

export default function DashboardStats({
  total = 0,
  present = 0,
  absent = 0,
  late = 0,
}) {
  return (
    <View style={styles.container}>

      <View style={styles.row}>
        <StatCard
          title="Employees"
          value={total}
          type="employees"
        />

        <StatCard
          title="Present"
          value={present}
          type="present"
        />
      </View>

      <View style={styles.row}>
        <StatCard
          title="Absent"
          value={absent}
          type="absent"
        />

        <StatCard
          title="Late"
          value={late}
          type="late"
        />
      </View>

    </View>
  );
}

const styles = StyleSheet.create({

  container: {
    marginTop: 20,
    marginBottom: 24,
    gap: 12,
  },

  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 12,
  },

});