import React, { useState, useEffect } from "react";
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity, ActivityIndicator, Alert, Image,
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { Ionicons } from "@expo/vector-icons";
import * as ImagePicker from "expo-image-picker";
import { fetchEmployeeProfile, uploadEmployeePhoto, getPhotoUrl } from "../../api/client";

function Section({ title, icon, children }) {
  return (
    <View style={sec.card}>
      <View style={sec.titleRow}>
        <Ionicons name={icon} size={18} color="#173B8C" />
        <Text style={sec.title}>{title}</Text>
      </View>
      {children}
    </View>
  );
}

const sec = StyleSheet.create({
  card:     { backgroundColor: "#FFFFFF", borderRadius: 18, padding: 18, marginBottom: 14, shadowColor: "#000", shadowOpacity: 0.04, shadowRadius: 8, shadowOffset: { width: 0, height: 2 }, elevation: 2 },
  titleRow: { flexDirection: "row", alignItems: "center", marginBottom: 16, paddingBottom: 12, borderBottomWidth: 1, borderColor: "#F1F5F9" },
  title:    { fontSize: 15, fontWeight: "700", color: "#0F172A", marginLeft: 8 },
});

function Field({ label, value }) {
  if (!value) return null;
  return (
    <View style={fld.row}>
      <Text style={fld.label}>{label}</Text>
      <Text style={fld.value}>{value}</Text>
    </View>
  );
}

const fld = StyleSheet.create({
  row:   { flexDirection: "row", justifyContent: "space-between", paddingVertical: 10, borderBottomWidth: 1, borderColor: "#F8FAFC" },
  label: { fontSize: 13, color: "#94A3B8", flex: 1 },
  value: { fontSize: 13, color: "#0F172A", fontWeight: "600", flex: 2, textAlign: "right" },
});

export default function ProfileScreen({ navigation }) {
  const [profile, setProfile]       = useState(null);
  const [loading, setLoading]       = useState(true);
  const [uploading, setUploading]   = useState(false);
  const [photoKey, setPhotoKey]     = useState(Date.now());

  useEffect(() => {
    fetchEmployeeProfile()
      .then(res => { if (res.data.ok) setProfile(res.data.profile); })
      .catch(() => Alert.alert("Error", "Failed to load profile."))
      .finally(() => setLoading(false));
  }, []);

  const handlePickPhoto = async () => {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== "granted") {
      Alert.alert("Permission Required", "Please allow access to your photo library.");
      return;
    }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      aspect: [1, 1],
      quality: 0.85,
    });
    if (result.canceled || !result.assets?.length) return;
    const asset = result.assets[0];
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("photo", {
        uri: asset.uri,
        name: "photo.jpg",
        type: "image/jpeg",
      });
      const res = await uploadEmployeePhoto(formData);
      if (res.data.ok) {
        setPhotoKey(Date.now());
        Alert.alert("Success", "Profile photo updated!");
      } else {
        Alert.alert("Error", res.data.msg || "Failed to upload photo.");
      }
    } catch (e) {
      Alert.alert("Error", e.response?.data?.msg || "Upload failed.");
    }
    setUploading(false);
  };

  const p = profile;

  return (
    <LinearGradient colors={["#F8FAFC", "#F3F7FD", "#EDF4FF"]} style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
          <Ionicons name="arrow-back" size={22} color="#173B8C" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>My Profile</Text>
        <View style={{ width: 40 }} />
      </View>

      {loading ? (
        <View style={styles.center}><ActivityIndicator size="large" color="#173B8C" /></View>
      ) : !p ? null : (
        <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
          {/* Hero */}
          <LinearGradient colors={["#173B8C", "#2563EB"]} style={styles.hero} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }}>
            <TouchableOpacity onPress={handlePickPhoto} disabled={uploading} style={styles.avatarWrapper}>
              <Image
                key={photoKey}
                source={{ uri: `${getPhotoUrl(p.employee_id)}?t=${photoKey}` }}
                style={styles.avatarImg}
                defaultSource={undefined}
                onError={() => {}}
              />
              <View style={styles.avatarCircleFallback} pointerEvents="none">
                <Ionicons name="person" size={36} color="#173B8C" />
              </View>
              <View style={styles.cameraOverlay}>
                {uploading
                  ? <ActivityIndicator color="#fff" size="small" />
                  : <Ionicons name="camera" size={18} color="#fff" />}
              </View>
            </TouchableOpacity>
            <Text style={styles.heroName}>{p.name}</Text>
            <Text style={styles.heroRole}>{p.role || "Employee"}</Text>
            <Text style={styles.heroDept}>{p.department || ""}</Text>
            {!!p.company_name && (
              <View style={styles.heroCompanyBadge}>
                <Ionicons name="business-outline" size={12} color="rgba(255,255,255,0.85)" />
                <Text style={styles.heroCompanyTxt}>{p.company_name}</Text>
              </View>
            )}
            <View style={styles.heroIdBadge}>
              <Ionicons name="card-outline" size={13} color="#FFFFFF" />
              <Text style={styles.heroId}>{p.employee_id}</Text>
            </View>
          </LinearGradient>

          {/* Personal Info */}
          <Section title="Personal Information" icon="person-outline">
            <Field label="Full Name"    value={p.name} />
            <Field label="Employee ID"  value={p.employee_id} />
            <Field label="Email"        value={p.email} />
            <Field label="Phone"        value={p.phone} />
            <Field label="Date of Birth" value={p.dob} />
            <Field label="Gender"       value={p.gender} />
            <Field label="Blood Group"  value={p.blood_group} />
            <Field label="Join Date"    value={p.join_date} />
          </Section>

          {/* Work Info */}
          <Section title="Work Information" icon="briefcase-outline">
            <Field label="Company"             value={p.company_name} />
            <Field label="Role / Designation" value={p.role} />
            <Field label="Department"          value={p.department} />
            <Field label="Daily Rate"          value={p.salary_per_day ? `₹ ${p.salary_per_day}` : null} />
          </Section>

          {/* Address */}
          {(p.address || p.city || p.state) && (
            <Section title="Address" icon="location-outline">
              <Field label="Address" value={p.address} />
              <Field label="City"    value={p.city} />
              <Field label="State"   value={p.state} />
              <Field label="Pincode" value={p.pincode} />
            </Section>
          )}

          {/* About */}
          {p.about_me && (
            <Section title="About Me" icon="information-circle-outline">
              <Text style={styles.aboutText}>{p.about_me}</Text>
            </Section>
          )}

          {/* Emergency Contact */}
          {(p.emergency_contact_name || p.emergency_contact_phone) && (
            <Section title="Emergency Contact" icon="call-outline">
              <Field label="Name"  value={p.emergency_contact_name} />
              <Field label="Phone" value={p.emergency_contact_phone} />
            </Section>
          )}

          {/* Bank & Identity */}
          {(p.bank_name || p.pan_number || p.aadhar_number) && (
            <Section title="Bank & Identity" icon="card-outline">
              <Field label="Bank Name"    value={p.bank_name} />
              <Field label="Account No."  value={p.bank_account} />
              <Field label="IFSC Code"    value={p.bank_ifsc} />
              <Field label="PAN Number"   value={p.pan_number} />
              <Field label="Aadhar No."   value={p.aadhar_number} />
            </Section>
          )}

          <View style={{ height: 40 }} />
        </ScrollView>
      )}
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    paddingTop: 55, paddingHorizontal: 20, paddingBottom: 16,
    backgroundColor: "#FFFFFF",
    shadowColor: "#000", shadowOpacity: 0.04, shadowRadius: 8, shadowOffset: { width: 0, height: 2 },
    elevation: 3,
  },
  backBtn:      { width: 40, height: 40, borderRadius: 12, backgroundColor: "#EEF4FF", justifyContent: "center", alignItems: "center" },
  headerTitle:  { fontSize: 18, fontWeight: "700", color: "#0F172A" },
  center:       { flex: 1, justifyContent: "center", alignItems: "center" },
  scroll:       { padding: 20 },
  hero: {
    borderRadius: 20, padding: 24, marginBottom: 16, alignItems: "center",
  },
  avatarWrapper: { position: "relative", marginBottom: 12 },
  avatarImg: { width: 88, height: 88, borderRadius: 44, borderWidth: 3, borderColor: "rgba(255,255,255,0.8)" },
  avatarCircleFallback: { position: "absolute", top: 0, left: 0, width: 88, height: 88, borderRadius: 44, backgroundColor: "#FFFFFF", justifyContent: "center", alignItems: "center", zIndex: -1 },
  cameraOverlay: { position: "absolute", bottom: 0, right: 0, width: 28, height: 28, borderRadius: 14, backgroundColor: "#173B8C", borderWidth: 2, borderColor: "#fff", justifyContent: "center", alignItems: "center" },
  avatarCircle: { width: 72, height: 72, borderRadius: 36, backgroundColor: "#FFFFFF", justifyContent: "center", alignItems: "center", marginBottom: 12 },
  heroName:     { color: "#FFFFFF", fontSize: 22, fontWeight: "800" },
  heroRole:     { color: "rgba(255,255,255,0.85)", fontSize: 14, marginTop: 4 },
  heroDept:     { color: "rgba(255,255,255,0.7)", fontSize: 13, marginTop: 2 },
  heroCompanyBadge: { flexDirection: "row", alignItems: "center", gap: 5, backgroundColor: "rgba(255,255,255,0.2)", paddingHorizontal: 12, paddingVertical: 5, borderRadius: 20, marginTop: 8 },
  heroCompanyTxt:   { color: "rgba(255,255,255,0.92)", fontSize: 12, fontWeight: "700" },
  heroIdBadge:  { flexDirection: "row", alignItems: "center", backgroundColor: "rgba(255,255,255,0.15)", paddingHorizontal: 14, paddingVertical: 6, borderRadius: 20, marginTop: 8 },
  heroId:       { color: "#FFFFFF", fontWeight: "700", fontSize: 13, marginLeft: 5 },
  aboutText:    { fontSize: 14, color: "#475569", lineHeight: 22 },
});
