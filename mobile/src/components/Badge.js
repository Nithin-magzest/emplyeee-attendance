import React from 'react';
import { Text, StyleSheet } from 'react-native';
import { COLORS } from '../config';

const MAP = {
  Pending:  { bg: COLORS.pendingBg,  fg: COLORS.pendingTxt  },
  Approved: { bg: COLORS.approvedBg, fg: COLORS.approvedTxt },
  Accepted: { bg: COLORS.approvedBg, fg: COLORS.approvedTxt },
  Declined: { bg: COLORS.declinedBg, fg: COLORS.declinedTxt },
  'Full Day':         { bg: COLORS.approvedBg, fg: COLORS.approvedTxt },
  'Late - Full Day':  { bg: COLORS.pendingBg,  fg: COLORS.pendingTxt  },
  'Half Day':         { bg: COLORS.pendingBg,  fg: COLORS.pendingTxt  },
  Absent:             { bg: COLORS.declinedBg, fg: COLORS.declinedTxt },
  Present:            { bg: COLORS.approvedBg, fg: COLORS.approvedTxt },
};

export default function Badge({ label, style }) {
  const theme = MAP[label] || { bg: 'rgba(255,255,255,0.1)', fg: '#fff' };
  return (
    <Text style={[styles.badge, { backgroundColor: theme.bg, color: theme.fg }, style]}>
      {label}
    </Text>
  );
}

const styles = StyleSheet.create({
  badge: {
    paddingHorizontal: 10,
    paddingVertical: 3,
    borderRadius: 20,
    fontSize: 11,
    fontWeight: '700',
    overflow: 'hidden',
    alignSelf: 'flex-start',
  },
});
