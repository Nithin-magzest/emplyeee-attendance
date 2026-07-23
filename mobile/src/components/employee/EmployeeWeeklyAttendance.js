import React from "react";
import {
  View,
  Text,
  StyleSheet,
} from "react-native";

const WEEK = [
  { day: "Mon", status: "present" },
  { day: "Tue", status: "present" },
  { day: "Wed", status: "late" },
  { day: "Thu", status: "leave" },
  { day: "Fri", status: "today" },
  { day: "Sat", status: "weekend" },
  { day: "Sun", status: "weekend" },
];

const COLORS = {
  present: "#22C55E",
  late: "#F59E0B",
  leave: "#EF4444",
  today: "#173B8C",
  weekend: "#CBD5E1",
};

const LABELS = {
  present: "P",
  late: "L",
  leave: "LV",
  today: "T",
  weekend: "-",
};

export default function EmployeeWeeklyAttendance({

  week = WEEK,

}) {

  return (

    <View style={styles.card}>

      <View style={styles.header}>

        <View>

          <Text style={styles.title}>
            Weekly Attendance
          </Text>

          <Text style={styles.subtitle}>
            This week's overview
          </Text>

        </View>

        <View style={styles.percentBox}>

          <Text style={styles.percent}>
            96%
          </Text>

        </View>

      </View>

      <View style={styles.row}>

        {week.map((item, index) => (

          <View
            key={index}
            style={styles.dayContainer}
          >

            <View
              style={[
                styles.circle,
                {
                  backgroundColor:
                    COLORS[item.status],
                },
              ]}
            >

              <Text style={styles.circleText}>
                {LABELS[item.status]}
              </Text>

            </View>

            <Text style={styles.day}>
              {item.day}
            </Text>

          </View>

        ))}

      </View>

      <View style={styles.legend}>

        <View style={styles.legendItem}>

          <View
            style={[
              styles.dot,
              { backgroundColor:"#22C55E" },
            ]}
          />

          <Text style={styles.legendText}>
            Present
          </Text>

        </View>

        <View style={styles.legendItem}>

          <View
            style={[
              styles.dot,
              { backgroundColor:"#F59E0B" },
            ]}
          />

          <Text style={styles.legendText}>
            Late
          </Text>

        </View>

        <View style={styles.legendItem}>

          <View
            style={[
              styles.dot,
              { backgroundColor:"#EF4444" },
            ]}
          />

          <Text style={styles.legendText}>
            Leave
          </Text>

        </View>

      </View>

    </View>

  );

}

const styles = StyleSheet.create({

  card:{

    backgroundColor:"#FFFFFF",

    borderRadius:22,

    padding:20,

    marginBottom:22,

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

    marginBottom:22,

  },

  title:{

    fontSize:18,

    fontWeight:"700",

    color:"#0F172A",

  },

  subtitle:{

    marginTop:3,

    color:"#64748B",

    fontSize:13,

  },

  percentBox:{

    backgroundColor:"#EEF4FF",

    paddingHorizontal:14,

    paddingVertical:8,

    borderRadius:18,

  },

  percent:{

    color:"#173B8C",

    fontWeight:"700",

    fontSize:13,

  },

  row:{

    flexDirection:"row",

    justifyContent:"space-between",

    marginBottom:20,

  },

  dayContainer:{

    alignItems:"center",

  },

  circle:{

    width:40,

    height:40,

    borderRadius:20,

    justifyContent:"center",

    alignItems:"center",

    marginBottom:8,

  },

  circleText:{

    color:"#FFFFFF",

    fontWeight:"800",

    fontSize:12,

  },

  day:{

    color:"#64748B",

    fontSize:12,

    fontWeight:"600",

  },

  legend:{

    flexDirection:"row",

    justifyContent:"space-around",

    borderTopWidth:1,

    borderTopColor:"#EEF2F7",

    paddingTop:16,

  },

  legendItem:{

    flexDirection:"row",

    alignItems:"center",

  },

  dot:{

    width:8,

    height:8,

    borderRadius:4,

    marginRight:6,

  },

  legendText:{

    fontSize:11,

    color:"#64748B",

    fontWeight:"600",

  },

});