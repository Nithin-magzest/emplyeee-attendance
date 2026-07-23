import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
} from 'react-native';

import { Ionicons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';

import AppCard from '../ui/AppCard';
import SectionHeader from '../ui/SectionHeader';

const MODULES = [

  {
    title: "Employees",
    subtitle: "Manage employees",
    icon: "people",
    color: "#2563EB",
    bg: "#EEF4FF",
    screen: "Employees",
  },

  {
    title: "Attendance",
    subtitle: "Daily records",
    icon: "calendar",
    color: "#16A34A",
    bg: "#ECFDF5",
    screen: "Attendance",
  },

  {
    title: "Leaves",
    subtitle: "Leave requests",
    icon: "document-text",
    color: "#EA580C",
    bg: "#FFF7ED",
    screen: "Leaves",
  },

  {
    title: "Resignations",
    subtitle: "Employee exits",
    icon: "exit",
    color: "#DC2626",
    bg: "#FEF2F2",
    screen: "Resignations",
  },

  {
    title: "Tickets",
    subtitle: "Support desk",
    icon: "ticket",
    color: "#7C3AED",
    bg: "#F5F3FF",
    screen: "Tickets",
  },

  {
    title: "Reports",
    subtitle: "Analytics",
    icon: "bar-chart",
    color: "#0891B2",
    bg: "#ECFEFF",
    screen: "Reports",
  },

];

export default function ModuleGrid() {

  const navigation = useNavigation();

  return (

    <View style={styles.container}>

      <SectionHeader
        title="Quick Actions"
        subtitle="Frequently used modules"
      />

      <View style={styles.grid}>

        {

          MODULES.map(item => (

            <TouchableOpacity

              key={item.title}

              activeOpacity={0.85}

              style={styles.wrapper}

              onPress={() => {

                if(item.screen){

                  navigation.navigate(item.screen);

                }

              }}

            >

              <AppCard style={styles.card}>

                <View style={styles.topRow}>

                  <View
                    style={[
                      styles.iconBox,
                      {
                        backgroundColor:item.bg,
                      },
                    ]}
                  >

                    <Ionicons
                      name={item.icon}
                      size={18}
                      color={item.color}
                    />

                  </View>

                  <Ionicons
                    name="arrow-forward"
                    size={15}
                    color="#CBD5E1"
                  />

                </View>

                <Text style={styles.title}>
                  {item.title}
                </Text>

                <Text style={styles.subtitle}>
                  {item.subtitle}
                </Text>

              </AppCard>

            </TouchableOpacity>

          ))

        }

      </View>

    </View>

  );

}

const styles = StyleSheet.create({

  container:{
    marginBottom:26,
  },

  grid:{
    flexDirection:"row",
    flexWrap:"wrap",
    justifyContent:"space-between",
    marginTop:14,
  },

  wrapper:{
    width:"48%",
    marginBottom:12,
  },

  card:{
    minHeight:110,
    padding:16,
    borderRadius:20,
  },

  topRow:{
    flexDirection:"row",
    justifyContent:"space-between",
    alignItems:"center",
    marginBottom:18,
  },

  iconBox:{
    width:42,
    height:42,
    borderRadius:14,
    justifyContent:"center",
    alignItems:"center",
  },

  title:{
    fontSize:15,
    fontWeight:"700",
    color:"#0F172A",
  },

  subtitle:{
    marginTop:4,
    fontSize:12,
    color:"#64748B",
    lineHeight:17,
  },

});