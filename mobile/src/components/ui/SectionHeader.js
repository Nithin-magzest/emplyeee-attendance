import React from 'react';
import {
  View,
  Text,
  Pressable,
  StyleSheet,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';

export default function SectionHeader({
  title,
  subtitle,
  actionText,
  onPress,
  icon,
}) {

  return (

    <View style={styles.container}>

      <View style={styles.left}>

        {icon && (

          <View style={styles.iconContainer}>

            <Ionicons
              name={icon}
              size={18}
              color="#173B8C"
            />

          </View>

        )}

        <View>

          <Text style={styles.title}>
            {title}
          </Text>

          {subtitle ? (

            <Text style={styles.subtitle}>
              {subtitle}
            </Text>

          ) : null}

        </View>

      </View>

      {actionText ? (

        <Pressable
          onPress={onPress}
          style={({ pressed }) => [
            styles.actionButton,
            pressed && styles.pressed,
          ]}
        >

          <Text style={styles.actionText}>
            {actionText}
          </Text>

          <Ionicons
            name="chevron-forward"
            size={16}
            color="#173B8C"
          />

        </Pressable>

      ) : null}

    </View>

  );

}

const styles = StyleSheet.create({

  container: {

    flexDirection: 'row',

    justifyContent: 'space-between',

    alignItems: 'center',

    marginBottom: 18,

  },

  left: {

    flexDirection: 'row',

    alignItems: 'center',

    flex: 1,

  },

  iconContainer: {

    width: 38,

    height: 38,

    borderRadius: 12,

    backgroundColor: '#EEF4FF',

    justifyContent: 'center',

    alignItems: 'center',

    marginRight: 12,

  },

  title: {

    fontSize: 20,

    fontWeight: '700',

    color: '#111827',

    letterSpacing: 0.2,

  },

  subtitle: {

    marginTop: 3,

    fontSize: 13,

    color: '#64748B',

    fontWeight: '500',

  },

  actionButton: {

    flexDirection: 'row',

    alignItems: 'center',

    paddingHorizontal: 12,

    paddingVertical: 8,

    borderRadius: 12,

    backgroundColor: '#F8FAFC',

  },

  pressed: {

    opacity: 0.85,

  },

  actionText: {

    color: '#173B8C',

    fontSize: 13,

    fontWeight: '700',

    marginRight: 4,

  },

});