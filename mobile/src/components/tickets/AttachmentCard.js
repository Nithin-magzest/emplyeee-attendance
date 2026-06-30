import React from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

export default function AttachmentCard({
  fileName = "",
  onUpload = () => {},
}) {
  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Ionicons
          name="attach-outline"
          size={22}
          color="#173B8C"
        />

        <Text style={styles.title}>
          Attachment
        </Text>
      </View>

      <Text style={styles.subtitle}>
        Attach screenshots or documents to help
        us understand your issue better.
      </Text>

      <TouchableOpacity
        activeOpacity={0.9}
        style={styles.uploadButton}
        onPress={onUpload}
      >
        <View style={styles.uploadIcon}>
          <Ionicons
            name="cloud-upload-outline"
            size={30}
            color="#173B8C"
          />
        </View>

        <View style={styles.uploadTextContainer}>
          <Text style={styles.uploadTitle}>
            Upload File
          </Text>

          <Text style={styles.uploadSubtitle}>
            JPG, PNG or PDF (Max 10 MB)
          </Text>
        </View>

        <Ionicons
          name="chevron-forward"
          size={22}
          color="#94A3B8"
        />
      </TouchableOpacity>

      {fileName !== "" && (
        <View style={styles.fileCard}>
          <View style={styles.fileLeft}>
            <View style={styles.fileIcon}>
              <Ionicons
                name="document-text"
                size={20}
                color="#22C55E"
              />
            </View>

            <View>
              <Text style={styles.fileName}>
                {fileName}
              </Text>

              <Text style={styles.fileStatus}>
                Ready to upload
              </Text>
            </View>
          </View>

          <Ionicons
            name="checkmark-circle"
            size={24}
            color="#22C55E"
          />
        </View>
      )}
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
  },

  title: {
    marginLeft: 10,

    fontSize: 18,

    fontWeight: "800",

    color: "#0F172A",
  },

  subtitle: {
    marginTop: 10,

    color: "#64748B",

    fontSize: 14,

    lineHeight: 22,

    marginBottom: 18,
  },

  uploadButton: {
    flexDirection: "row",

    alignItems: "center",

    borderWidth: 2,

    borderStyle: "dashed",

    borderColor: "#CBD5E1",

    borderRadius: 18,

    padding: 18,

    backgroundColor: "#F8FAFC",
  },

  uploadIcon: {
    width: 56,
    height: 56,

    borderRadius: 28,

    backgroundColor: "#EEF4FF",

    justifyContent: "center",
    alignItems: "center",
  },

  uploadTextContainer: {
    flex: 1,
    marginLeft: 16,
  },

  uploadTitle: {
    fontSize: 16,

    fontWeight: "700",

    color: "#0F172A",
  },

  uploadSubtitle: {
    marginTop: 4,

    fontSize: 13,

    color: "#64748B",
  },

  fileCard: {
    marginTop: 18,

    backgroundColor: "#ECFDF5",

    borderRadius: 16,

    padding: 14,

    flexDirection: "row",

    justifyContent: "space-between",

    alignItems: "center",
  },

  fileLeft: {
    flexDirection: "row",
    alignItems: "center",
  },

  fileIcon: {
    width: 42,
    height: 42,

    borderRadius: 21,

    backgroundColor: "#FFFFFF",

    justifyContent: "center",
    alignItems: "center",

    marginRight: 12,
  },

  fileName: {
    fontSize: 15,

    fontWeight: "700",

    color: "#0F172A",
  },

  fileStatus: {
    marginTop: 3,

    fontSize: 12,

    color: "#16A34A",

    fontWeight: "600",
  },
});