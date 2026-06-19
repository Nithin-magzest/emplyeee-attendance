import React from 'react';
import {
  View,
  Pressable,
  StyleSheet,
} from 'react-native';

const AppCard = ({
  children,
  style,
  onPress,
  padding = 20,
  radius = 24,
  elevated = true,
  border = true,
}) => {
  const cardStyle = [
    styles.card,
    {
      padding,
      borderRadius: radius,
      borderWidth: border ? 1 : 0,
    },
    elevated && styles.shadow,
    style,
  ];

  if (onPress) {
    return (
      <Pressable
        onPress={onPress}
        android_ripple={{ color: '#E8EEF9' }}
        style={({ pressed }) => [
          cardStyle,
          pressed && styles.pressed,
        ]}
      >
        {children}
      </Pressable>
    );
  }

  return (
    <View style={cardStyle}>
      {children}
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#FFFFFF',
    borderColor: '#E8EDF5',
    overflow: 'hidden',
  },

  shadow: {
    shadowColor: '#0F172A',
    shadowOpacity: 0.08,
    shadowRadius: 18,
    shadowOffset: {
      width: 0,
      height: 8,
    },
    elevation: 6,
  },

  pressed: {
    opacity: 0.95,
    transform: [
      {
        scale: 0.985,
      },
    ],
  },
});

export default AppCard;