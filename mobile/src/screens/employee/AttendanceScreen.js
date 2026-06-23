import React, { useEffect, useState } from "react";
import AttendanceScannerModal from "../AttendanceScannerModal";

export default function AttendanceScreen({ navigation }) {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    setVisible(true);
  }, []);

  return (
    <AttendanceScannerModal
      visible={visible}
      onClose={() => {
        setVisible(false);
        navigation.navigate("Home");
      }}
      onSuccess={() => {
        setVisible(false);
        navigation.navigate("Home");
      }}
    />
  );
}