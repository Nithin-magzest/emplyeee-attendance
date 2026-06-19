import React from 'react';
import {
  View,
  Text,
  StyleSheet,
} from 'react-native';

export default function Divider({

  text,

  marginVertical = 20,

  color = '#E5EAF2',

  textColor = '#94A3B8',

}) {

  if (text) {

    return (

      <View
        style={[
          styles.row,
          {
            marginVertical,
          },
        ]}
      >

        <View
          style={[
            styles.line,
            {
              backgroundColor: color,
            },
          ]}
        />

        <Text
          style={[
            styles.text,
            {
              color: textColor,
            },
          ]}
        >
          {text}
        </Text>

        <View
          style={[
            styles.line,
            {
              backgroundColor: color,
            },
          ]}
        />

      </View>

    );

  }

  return (

    <View

      style={[
        styles.singleDivider,
        {
          backgroundColor: color,
          marginVertical,
        },
      ]}

    />

  );

}

const styles = StyleSheet.create({

  singleDivider: {

    height: 1,

    width: '100%',

  },

  row: {

    flexDirection: 'row',

    alignItems: 'center',

  },

  line: {

    flex: 1,

    height: 1,

  },

  text: {

    marginHorizontal: 14,

    fontSize: 12,

    fontWeight: '600',

    letterSpacing: 0.3,

  },

});