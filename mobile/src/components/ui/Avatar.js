import React from 'react';
import {
  View,
  Text,
  Image,
  StyleSheet,
} from 'react-native';

const SIZES = {
  xs: 28,
  sm: 40,
  md: 52,
  lg: 64,
  xl: 84,
};

export default function Avatar({
  source,
  name = '',
  size = 'md',
  online = false,
  style,
}) {

  const avatarSize = SIZES[size] || SIZES.md;

  const initials = name
    .trim()
    .split(' ')
    .slice(0, 2)
    .map(word => word.charAt(0).toUpperCase())
    .join('');

  return (
    <View
      style={[
        styles.wrapper,
        {
          width: avatarSize,
          height: avatarSize,
        },
        style,
      ]}
    >
      {source ? (
        <Image
          source={source}
          style={{
            width: avatarSize,
            height: avatarSize,
            borderRadius: avatarSize / 2,
          }}
        />
      ) : (
        <View
          style={[
            styles.placeholder,
            {
              width: avatarSize,
              height: avatarSize,
              borderRadius: avatarSize / 2,
            },
          ]}
        >
          <Text
            style={[
              styles.initials,
              {
                fontSize: avatarSize * 0.34,
              },
            ]}
          >
            {initials || '?'}
          </Text>
        </View>
      )}

      {online && (
        <View
          style={[
            styles.status,
            {
              width: avatarSize * 0.24,
              height: avatarSize * 0.24,
              borderRadius: avatarSize * 0.12,
              right: avatarSize * 0.02,
              bottom: avatarSize * 0.02,
            },
          ]}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({

  wrapper: {
    position: 'relative',
  },

  placeholder: {
    backgroundColor: '#EAF2FF',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#D8E4F6',
  },

  initials: {
    fontWeight: '700',
    color: '#173B8C',
  },

  status: {
    position: 'absolute',
    backgroundColor: '#22C55E',
    borderWidth: 2,
    borderColor: '#FFFFFF',
  },

});