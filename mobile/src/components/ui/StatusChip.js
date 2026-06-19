import React from 'react';
import {
  View,
  Text,
  StyleSheet,
} from 'react-native';

import { Ionicons } from '@expo/vector-icons';

const STATUS = {

  Present: {
    bg: '#ECFDF5',
    color: '#15803D',
    icon: 'checkmark-circle',
  },

  Absent: {
    bg: '#FEF2F2',
    color: '#DC2626',
    icon: 'close-circle',
  },

  Late: {
    bg: '#FFF7ED',
    color: '#EA580C',
    icon: 'time',
  },

  Pending: {
    bg: '#FEFCE8',
    color: '#CA8A04',
    icon: 'time-outline',
  },

  Approved: {
    bg: '#ECFDF5',
    color: '#16A34A',
    icon: 'checkmark-done-circle',
  },

  Rejected: {
    bg: '#FEF2F2',
    color: '#DC2626',
    icon: 'close-circle',
  },

  Resigned: {
    bg: '#F8FAFC',
    color: '#475569',
    icon: 'exit-outline',
  },

  Active: {
    bg: '#EFF6FF',
    color: '#2563EB',
    icon: 'radio-button-on',
  },

};

export default function StatusChip({

  label = 'Pending',

  style,

}) {

  const theme =
    STATUS[label] ||
    STATUS.Pending;

  return (

    <View

      style={[
        styles.container,
        {
          backgroundColor: theme.bg,
        },
        style,
      ]}

    >

      <Ionicons
        name={theme.icon}
        size={14}
        color={theme.color}
      />

      <Text

        style={[
          styles.text,
          {
            color: theme.color,
          },
        ]}

      >

        {label}

      </Text>

    </View>

  );

}

const styles = StyleSheet.create({

  container: {

    flexDirection: 'row',

    alignItems: 'center',

    alignSelf: 'flex-start',

    paddingHorizontal: 12,

    paddingVertical: 6,

    borderRadius: 30,

  },

  text: {

    marginLeft: 6,

    fontSize: 12,

    fontWeight: '700',

    letterSpacing: 0.2,

  },

});