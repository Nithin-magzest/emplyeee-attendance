import React, { useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Image,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

export default function EmployeeHeroCard({
  employeeName,
  designation,
  employeeId,
  date,
  attendance,
  onCheckIn,
  checking,
  onMenu,
  onLogout,
  photoUrl,
  onScanQR,
}) {
  const [photoError, setPhotoError] = useState(false);

  const checkedIn =
    attendance?.login_time &&
    !attendance?.logout_time;

  const completed =
    attendance?.login_time &&
    attendance?.logout_time;

  const checkIn =
    attendance?.login_time
      ? attendance.login_time.slice(0,5)
      : "--:--";

  const checkOut =
    attendance?.logout_time
      ? attendance.logout_time.slice(0,5)
      : "--:--";

  const workedHours =
    attendance?.working_hours ||
    attendance?.hours ||
    "0h 00m";

  const greeting = () => {

    const hour = new Date().getHours();

    if(hour < 12) return "Good Morning";

    if(hour < 17) return "Good Afternoon";

    return "Good Evening";

  };

  const status = completed
    ? "Completed"
    : checkedIn
    ? "Working"
    : "Not Checked In";

  return (

    <View style={styles.card}>

      {/* Top Row */}
      <View style={styles.topRow}>
        <TouchableOpacity style={styles.iconBtn} onPress={onScanQR}>
          <Ionicons name="qr-code-outline" size={22} color="#173B8C" />
        </TouchableOpacity>
        <TouchableOpacity style={styles.iconBtn} onPress={onLogout}>
          <Ionicons name="log-out-outline" size={21} color="#173B8C" />
        </TouchableOpacity>
      </View>

      {/* User */}

      <View style={styles.userRow}>

        <View style={styles.avatar}>
          {photoUrl && !photoError ? (
            <Image
              source={{ uri: photoUrl }}
              style={styles.avatarImg}
              onError={() => setPhotoError(true)}
            />
          ) : (
            <Ionicons name="person" size={32} color="#173B8C" />
          )}
          <View style={styles.onlineDot} />
        </View>

        <View style={{flex:1}}>

          <Text style={styles.greeting}>
            {greeting()}
          </Text>

          <Text style={styles.name}>
            {employeeName || "Employee"}
          </Text>

          <Text style={styles.designation}>
            {designation || "Software Engineer"}
          </Text>

        </View>

      </View>

      {/* Divider */}

      <View style={styles.divider}/>

      {/* Info */}

      <View style={styles.infoRow}>

        <View style={styles.badge}>

          <Ionicons
            name="card-outline"
            size={13}
            color="#173B8C"
          />

          <Text style={styles.badgeText}>
            {employeeId}
          </Text>

        </View>

        <View style={styles.dateRow}>

          <Ionicons
            name="calendar-outline"
            size={14}
            color="#94A3B8"
          />

          <Text style={styles.date}>
            {date}
          </Text>

        </View>

      </View>

      {/* Attendance */}

      <View style={styles.attendanceCard}>

        <View style={styles.attRow}>

          <View style={styles.attBox}>

            <Ionicons
              name="log-in-outline"
              size={18}
              color="#22C55E"
            />

            <Text style={styles.attLabel}>
              Check In
            </Text>

            <Text style={styles.attTime}>
              {checkIn}
            </Text>

          </View>

          <View style={styles.attBox}>

            <Ionicons
              name="log-out-outline"
              size={18}
              color="#EF4444"
            />

            <Text style={styles.attLabel}>
              Check Out
            </Text>

            <Text style={styles.attTime}>
              {checkOut}
            </Text>

          </View>

        </View>

        <View style={styles.bottomRow}>

          <View>

            <Text style={styles.smallTitle}>
              Status
            </Text>

            <Text style={styles.status}>
              {status}
            </Text>

          </View>

          <View>

            <Text style={styles.smallTitle}>
              Hours Today
            </Text>

            <Text style={styles.status}>
              {workedHours}
            </Text>

          </View>

        </View>

      </View>

      {/* Button */}

      {!completed && (

        <TouchableOpacity
          style={[
            styles.button,
            checkedIn && styles.checkout,
          ]}
          disabled={checking}
          onPress={onCheckIn}
        >

          <Ionicons
            name={
              checkedIn
              ? "log-out-outline"
              : "log-in-outline"
            }
            size={20}
            color="#FFF"
          />

          <Text style={styles.buttonText}>

            {checkedIn
              ? "Check Out"
              : "Check In"}

          </Text>

        </TouchableOpacity>

      )}

    </View>

  );

}

const styles = StyleSheet.create({

  card:{
    backgroundColor:"#FFFFFF",
    borderRadius:24,
    padding:20,
    marginBottom:20,
    shadowColor:"#000",
    shadowOpacity:0.08,
    shadowRadius:14,
    shadowOffset:{width:0,height:8},
    elevation:5,
  },

  topRow:{
    flexDirection:"row",
    justifyContent:"space-between",
    marginBottom:18,
  },

  iconBtn:{
    width:42,
    height:42,
    borderRadius:14,
    backgroundColor:"#F3F7FD",
    justifyContent:"center",
    alignItems:"center",
  },

  userRow:{
    flexDirection:"row",
    alignItems:"center",
  },

  avatar:{
    width:72,
    height:72,
    borderRadius:36,
    backgroundColor:"#EEF4FF",
    justifyContent:"center",
    alignItems:"center",
    marginRight:16,
    position:"relative",
    overflow:"hidden",
  },

  avatarImg:{
    width:72,
    height:72,
    borderRadius:36,
  },

  onlineDot:{
    position:"absolute",
    bottom:5,
    right:6,
    width:14,
    height:14,
    borderRadius:7,
    backgroundColor:"#22C55E",
    borderWidth:2,
    borderColor:"#FFF",
  },

  greeting:{
    color:"#64748B",
    fontSize:13,
    fontWeight:"600",
  },

  name:{
    fontSize:28,
    fontWeight:"800",
    color:"#0F172A",
    marginTop:3,
  },

  designation:{
    marginTop:4,
    color:"#64748B",
    fontSize:15,
  },

  divider:{
    height:1,
    backgroundColor:"#EEF2F7",
    marginVertical:18,
  },

  infoRow:{
    flexDirection:"row",
    justifyContent:"space-between",
    alignItems:"center",
    marginBottom:18,
  },

  badge:{
    flexDirection:"row",
    alignItems:"center",
    backgroundColor:"#EEF4FF",
    paddingHorizontal:12,
    paddingVertical:8,
    borderRadius:20,
  },

  badgeText:{
    marginLeft:6,
    color:"#173B8C",
    fontWeight:"700",
    fontSize:13,
  },

  dateRow:{
    flexDirection:"row",
    alignItems:"center",
  },

  date:{
    marginLeft:5,
    color:"#64748B",
    fontSize:13,
  },

  attendanceCard:{
    backgroundColor:"#F8FAFC",
    borderRadius:18,
    padding:18,
  },

  attRow:{
    flexDirection:"row",
    justifyContent:"space-between",
  },

  attBox:{
    flex:1,
    alignItems:"center",
  },

  attLabel:{
    color:"#64748B",
    marginTop:6,
    fontSize:13,
  },

  attTime:{
    marginTop:6,
    fontSize:24,
    fontWeight:"800",
    color:"#0F172A",
  },

  bottomRow:{
    flexDirection:"row",
    justifyContent:"space-between",
    marginTop:20,
    paddingTop:18,
    borderTopWidth:1,
    borderColor:"#E5E7EB",
  },

  smallTitle:{
    color:"#94A3B8",
    fontSize:12,
  },

  status:{
    marginTop:4,
    fontSize:16,
    fontWeight:"700",
    color:"#0F172A",
  },

  button:{
    marginTop:20,
    height:56,
    borderRadius:18,
    backgroundColor:"#173B8C",
    flexDirection:"row",
    justifyContent:"center",
    alignItems:"center",
  },

  checkout:{
    backgroundColor:"#EF4444",
  },

  buttonText:{
    color:"#FFF",
    fontWeight:"700",
    fontSize:16,
    marginLeft:8,
  },

});