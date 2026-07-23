import React from "react";
import {
  View,
  Text,
  StyleSheet,
  Image,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

export default function EmployeeProfileCard({

  employee = {},

}) {

  return (

    <View style={styles.container}>

      <View style={styles.header}>

        <Text style={styles.title}>
          Employee Profile
        </Text>

        <Ionicons
          name="person-circle-outline"
          size={22}
          color="#173B8C"
        />

      </View>

      <View style={styles.profileRow}>

        {

          employee.photo ? (

            <Image
              source={{ uri: employee.photo }}
              style={styles.avatar}
            />

          ) : (

            <View style={styles.avatarPlaceholder}>

              <Ionicons
                name="person"
                size={34}
                color="#173B8C"
              />

            </View>

          )

        }

        <View style={styles.info}>

          <Text style={styles.name}>
            {employee.name || "John Doe"}
          </Text>

          <Text style={styles.designation}>
            {employee.designation || "Software Engineer"}
          </Text>

          <Text style={styles.department}>
            {employee.department || "Engineering"}
          </Text>

        </View>

      </View>

      <View style={styles.divider} />

      <View style={styles.item}>

        <Ionicons
          name="card-outline"
          size={18}
          color="#64748B"
        />

        <Text style={styles.label}>
          Employee ID
        </Text>

        <Text style={styles.value}>
          {employee.employee_id || "EMP001"}
        </Text>

      </View>

      <View style={styles.item}>

        <Ionicons
          name="mail-outline"
          size={18}
          color="#64748B"
        />

        <Text style={styles.label}>
          Email
        </Text>

        <Text
          numberOfLines={1}
          style={styles.value}
        >
          {employee.email || "john@example.com"}
        </Text>

      </View>

      <View style={styles.item}>

        <Ionicons
          name="business-outline"
          size={18}
          color="#64748B"
        />

        <Text style={styles.label}>
          Department
        </Text>

        <Text style={styles.value}>
          {employee.department || "Engineering"}
        </Text>

      </View>

      <View style={styles.item}>

        <Ionicons
          name="call-outline"
          size={18}
          color="#64748B"
        />

        <Text style={styles.label}>
          Phone
        </Text>

        <Text style={styles.value}>
          {employee.phone || "+91 9876543210"}
        </Text>

      </View>

    </View>

  );

}

const styles = StyleSheet.create({

  container:{

    backgroundColor:"#FFFFFF",

    borderRadius:22,

    padding:20,

    marginBottom:24,

    borderWidth:1,

    borderColor:"#E8EDF5",

    shadowColor:"#0F172A",

    shadowOpacity:.05,

    shadowRadius:14,

    shadowOffset:{
      width:0,
      height:6,
    },

    elevation:4,

  },

  header:{

    flexDirection:"row",

    justifyContent:"space-between",

    alignItems:"center",

    marginBottom:18,

  },

  title:{

    fontSize:18,

    fontWeight:"700",

    color:"#0F172A",

  },

  profileRow:{

    flexDirection:"row",

    alignItems:"center",

    marginBottom:18,

  },

  avatar:{

    width:72,

    height:72,

    borderRadius:36,

    marginRight:16,

  },

  avatarPlaceholder:{

    width:72,

    height:72,

    borderRadius:36,

    backgroundColor:"#EEF4FF",

    justifyContent:"center",

    alignItems:"center",

    marginRight:16,

  },

  info:{

    flex:1,

  },

  name:{

    fontSize:20,

    fontWeight:"700",

    color:"#0F172A",

  },

  designation:{

    marginTop:4,

    fontSize:14,

    color:"#64748B",

  },

  department:{

    marginTop:4,

    fontSize:13,

    color:"#173B8C",

    fontWeight:"600",

  },

  divider:{

    height:1,

    backgroundColor:"#EEF2F7",

    marginBottom:16,

  },

  item:{

    flexDirection:"row",

    alignItems:"center",

    paddingVertical:10,

  },

  label:{

    marginLeft:12,

    flex:1,

    color:"#64748B",

    fontSize:14,

  },

  value:{

    color:"#0F172A",

    fontWeight:"600",

    fontSize:14,

    maxWidth:"45%",

    textAlign:"right",

  },

});