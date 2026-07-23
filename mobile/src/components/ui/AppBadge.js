import React from 'react';
import {
  View,
  Text,
  StyleSheet,
} from 'react-native';

const THEMES = {

  primary: {
    background: '#EAF2FF',
    color: '#173B8C',
    border: '#D8E6FF',
  },

  success: {
    background: '#ECFDF5',
    color: '#15803D',
    border: '#BBF7D0',
  },

  warning: {
    background: '#FFF7ED',
    color: '#C2410C',
    border: '#FED7AA',
  },

  danger: {
    background: '#FEF2F2',
    color: '#DC2626',
    border: '#FECACA',
  },

  neutral: {
    background: '#F8FAFC',
    color: '#475569',
    border: '#E2E8F0',
  },

};

export default function AppBadge({

  label,

  variant = 'primary',

  size = 'md',

  style,

}) {

  const theme = THEMES[variant] || THEMES.primary;

  const small = size === 'sm';

  return (

    <View
      style={[
        styles.badge,
        {
          backgroundColor: theme.background,
          borderColor: theme.border,

          paddingHorizontal: small ? 8 : 12,
          paddingVertical: small ? 4 : 6,
        },
        style,
      ]}
    >

      <Text
        style={[
          styles.text,
          {
            color: theme.color,
            fontSize: small ? 11 : 12,
          },
        ]}
      >

        {label}

      </Text>

    </View>

  );

}

const styles = StyleSheet.create({

  badge: {

    alignSelf: 'flex-start',

    borderRadius: 999,

    borderWidth: 1,

    justifyContent: 'center',

    alignItems: 'center',

  },

  text: {

    fontWeight: '700',

    letterSpacing: 0.2,

  },

});