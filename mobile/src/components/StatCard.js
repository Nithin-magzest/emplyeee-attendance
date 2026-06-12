import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { COLORS } from '../config';

export default function StatCard({ num, label, color }) {
  return (
    <View style={styles.card}>
      <Text style={[styles.num, { color: color || COLORS.blueLight }]}>{num}</Text>
      <Text style={styles.lbl}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flex: 1,
    backgroundColor: COLORS.card,
    borderRadius: 14,
    padding: 16,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: COLORS.border,
    margin: 4,
  },
  num: {
    fontSize: 28,
    fontWeight: '700',
    marginBottom: 4,
  },
  lbl: {
    fontSize: 11,
    color: COLORS.textMuted,
    textAlign: 'center',
  },
});
