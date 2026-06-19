import React from "react";
import {
  View,
  TouchableOpacity,
  Text,
  StyleSheet,
  ActivityIndicator,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

export default function EmployeeCheckInButton({

  checkedIn = false,

  completed = false,

  loading = false,

  onPress,

}) {

  if (completed) {

    return null;

  }

  return (

    <TouchableOpacity

      activeOpacity={0.9}

      disabled={loading}

      onPress={onPress}

      style={[

        styles.button,

        checkedIn
          ? styles.checkout
          : styles.checkin,

      ]}

    >

      {loading ? (

        <ActivityIndicator
          color="#FFFFFF"
        />

      ) : (

        <>

          <View style={styles.iconContainer}>

            <Ionicons

              name={
                checkedIn
                  ? "log-out-outline"
                  : "log-in-outline"
              }

              size={22}

              color="#FFFFFF"

            />

          </View>

          <Text style={styles.title}>

            {checkedIn
              ? "Check Out"
              : "Check In"}

          </Text>

        </>

      )}

    </TouchableOpacity>

  );

}

const styles = StyleSheet.create({

  button: {

    height: 58,

    borderRadius: 18,

    flexDirection: "row",

    justifyContent: "center",

    alignItems: "center",

    marginTop: 20,

    shadowColor: "#0F172A",

    shadowOpacity: 0.10,

    shadowRadius: 12,

    shadowOffset: {

      width: 0,

      height: 5,

    },

    elevation: 5,

  },

  checkin: {

    backgroundColor: "#173B8C",

  },

  checkout: {

    backgroundColor: "#EF4444",

  },

  iconContainer: {

    width: 34,

    height: 34,

    borderRadius: 17,

    backgroundColor: "rgba(255,255,255,0.15)",

    justifyContent: "center",

    alignItems: "center",

    marginRight: 10,

  },

  title: {

    color: "#FFFFFF",

    fontSize: 16,

    fontWeight: "700",

    letterSpacing: 0.3,

  },

});