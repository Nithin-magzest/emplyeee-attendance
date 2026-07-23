import React from "react";
import {
  View,
  Text,
  StyleSheet,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

function DocumentRow({
  icon,
  title,
  status,
}) {
  const completed = status === "Verified";

  return (
    <View style={styles.row}>
      <View style={styles.left}>
        <View
          style={[
            styles.iconContainer,
            {
              backgroundColor: completed
                ? "#ECFDF5"
                : "#FFF7ED",
            },
          ]}
        >
          <Ionicons
            name={icon}
            size={20}
            color={
              completed
                ? "#22C55E"
                : "#F59E0B"
            }
          />
        </View>

        <Text style={styles.documentName}>
          {title}
        </Text>
      </View>

      <View
        style={[
          styles.badge,
          {
            backgroundColor: completed
              ? "#ECFDF5"
              : "#FFF7ED",
          },
        ]}
      >
        <Text
          style={[
            styles.badgeText,
            {
              color: completed
                ? "#16A34A"
                : "#D97706",
            },
          ]}
        >
          {status}
        </Text>
      </View>
    </View>
  );
}

export default function DocumentStatusCard({
  documents = [],
}) {
  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Ionicons
          name="document-text-outline"
          size={22}
          color="#173B8C"
        />

        <Text style={styles.title}>
          Required Documents
        </Text>
      </View>

      {documents.map((doc, index) => (
        <View
          key={`${doc.title}-${index}`}
          style={[
            styles.wrapper,
            index === documents.length - 1 && {
              marginBottom: 0,
            },
          ]}
        >
          <DocumentRow
            icon={doc.icon}
            title={doc.title}
            status={doc.status}
          />
        </View>
      ))}
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
    shadowOpacity: 0.04,
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

  wrapper: {
    marginBottom: 14,
  },

  row: {
    flexDirection: "row",

    justifyContent: "space-between",

    alignItems: "center",
  },

  left: {
    flexDirection: "row",

    alignItems: "center",

    flex: 1,
  },

  iconContainer: {
    width: 48,
    height: 48,

    borderRadius: 14,

    justifyContent: "center",
    alignItems: "center",
  },

  documentName: {
    marginLeft: 14,

    flex: 1,

    fontSize: 15,

    fontWeight: "700",

    color: "#0F172A",
  },

  badge: {
    paddingHorizontal: 12,
    paddingVertical: 6,

    borderRadius: 30,
  },

  badgeText: {
    fontSize: 12,

    fontWeight: "800",
  },
});