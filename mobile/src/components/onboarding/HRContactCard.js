import React from "react";
import {
  View,
  Text,
 StyleSheet,
  TouchableOpacity,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

export default function HRContactCard({
  name,
  designation,
  email,
  phone,
  onCall = () => {},
  onEmail = () => {},
}) {
  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Ionicons
          name="people-outline"
          size={22}
          color="#173B8C"
        />

        <Text style={styles.title}>
          HR Contact
        </Text>
      </View>

      <View style={styles.profileSection}>
        <View style={styles.avatar}>
          <Ionicons
            name="person"
            size={40}
            color="#173B8C"
          />
        </View>

        <View style={styles.info}>
          <Text style={styles.name}>
            {name}
          </Text>

          <Text style={styles.designation}>
            {designation}
          </Text>
        </View>
      </View>

      <View style={styles.divider} />

      <View style={styles.detailRow}>
        <View style={styles.iconBox}>
          <Ionicons
            name="mail-outline"
            size={18}
            color="#173B8C"
          />
        </View>

        <View style={styles.detailContent}>
          <Text style={styles.label}>
            Email
          </Text>

          <Text style={styles.value}>
            {email}
          </Text>
        </View>
      </View>

      <View style={styles.detailRow}>
        <View style={styles.iconBox}>
          <Ionicons
            name="call-outline"
            size={18}
            color="#173B8C"
          />
        </View>

        <View style={styles.detailContent}>
          <Text style={styles.label}>
            Phone
          </Text>

          <Text style={styles.value}>
            {phone}
          </Text>
        </View>
      </View>

      <View style={styles.buttonRow}>
        <TouchableOpacity
          activeOpacity={0.85}
          style={styles.callButton}
          onPress={onCall}
        >
          <Ionicons
            name="call"
            size={18}
            color="#FFFFFF"
          />

          <Text style={styles.buttonText}>
            Call HR
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          activeOpacity={0.85}
          style={styles.emailButton}
          onPress={onEmail}
        >
          <Ionicons
            name="mail"
            size={18}
            color="#173B8C"
          />

          <Text style={styles.emailText}>
            Email
          </Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: "#FFFFFF",

    borderRadius: 22,

    padding: 20,

    marginBottom: 22,

    borderWidth: 1,
    borderColor: "#E8EDF3",

    shadowColor: "#000",
    shadowOpacity: 0.05,
    shadowRadius: 10,
    shadowOffset: {
      width: 0,
      height: 5,
    },

    elevation: 2,
  },

  header: {
    flexDirection: "row",
    alignItems: "center",

    marginBottom: 18,
  },

  title: {
    marginLeft: 10,

    fontSize: 18,

    fontWeight: "800",

    color: "#0F172A",
  },

  profileSection: {
    flexDirection: "row",
    alignItems: "center",
  },

  avatar: {
    width: 72,
    height: 72,

    borderRadius: 36,

    backgroundColor: "#EEF4FF",

    justifyContent: "center",
    alignItems: "center",
  },

  info: {
    marginLeft: 18,
    flex: 1,
  },

  name: {
    fontSize: 20,

    fontWeight: "800",

    color: "#0F172A",
  },

  designation: {
    marginTop: 5,

    fontSize: 14,

    color: "#64748B",

    fontWeight: "600",
  },

  divider: {
    height: 1,

    backgroundColor: "#EEF2F7",

    marginVertical: 18,
  },

  detailRow: {
    flexDirection: "row",

    alignItems: "center",

    marginBottom: 16,
  },

  iconBox: {
    width: 42,
    height: 42,

    borderRadius: 14,

    backgroundColor: "#EEF4FF",

    justifyContent: "center",
    alignItems: "center",
  },

  detailContent: {
    flex: 1,

    marginLeft: 14,
  },

  label: {
    fontSize: 13,

    fontWeight: "600",

    color: "#64748B",
  },

  value: {
    marginTop: 4,

    fontSize: 15,

    fontWeight: "700",

    color: "#0F172A",
  },

  buttonRow: {
    flexDirection: "row",

    marginTop: 10,
  },

  callButton: {
    flex: 1,

    height: 52,

    borderRadius: 16,

    backgroundColor: "#173B8C",

    flexDirection: "row",

    justifyContent: "center",
    alignItems: "center",

    marginRight: 8,
  },

  emailButton: {
    flex: 1,

    height: 52,

    borderRadius: 16,

    backgroundColor: "#EEF4FF",

    flexDirection: "row",

    justifyContent: "center",
    alignItems: "center",

    marginLeft: 8,
  },

  buttonText: {
    marginLeft: 8,

    color: "#FFFFFF",

    fontWeight: "700",

    fontSize: 15,
  },

  emailText: {
    marginLeft: 8,

    color: "#173B8C",

    fontWeight: "700",

    fontSize: 15,
  },
});