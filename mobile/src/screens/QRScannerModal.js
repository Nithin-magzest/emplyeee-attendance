import React, { useState, useEffect } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity, Modal, Alert, ActivityIndicator,
} from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { Ionicons } from '@expo/vector-icons';
import { employeeLogin, employeeCheckin } from '../api/client';
import { useAuth } from '../store/AuthContext';

export default function QRScannerModal({ visible, onClose }) {
  const { signIn } = useAuth();
  const [permission, requestPermission] = useCameraPermissions();
  const [scanned, setScanned]       = useState(false);
  const [processing, setProcessing] = useState(false);
  const [statusMsg, setStatusMsg]   = useState('');

  useEffect(() => {
    if (visible) {
      setScanned(false);
      setProcessing(false);
      setStatusMsg('');
    }
  }, [visible]);

  const handleScan = async ({ data }) => {
    if (scanned || processing) return;
    setScanned(true);
    setProcessing(true);
    setStatusMsg('Logging in…');

    const empId = data.trim();
    try {
      const loginRes = await employeeLogin(empId);
      if (!loginRes.data.ok) {
        Alert.alert('Not Found', loginRes.data.msg || 'Employee not found.', [
          { text: 'Scan Again', onPress: () => { setScanned(false); setProcessing(false); setStatusMsg(''); } },
          { text: 'Cancel', onPress: onClose },
        ]);
        return;
      }

      await signIn(loginRes.data.token, {
        role: 'employee',
        name: loginRes.data.name,
        employeeId: loginRes.data.employee_id,
      });

      setStatusMsg('Marking attendance…');
      try {
        const checkinRes = await employeeCheckin();
        if (checkinRes.data.ok) {
          const title = checkinRes.data.action === 'login' ? '✅ Checked In!' : '✅ Checked Out!';
          Alert.alert(title, `${loginRes.data.name}\n${checkinRes.data.status}\nTime: ${checkinRes.data.time}`);
        }
      } catch (_) {}

      onClose();
    } catch (e) {
      Alert.alert('Error', e.response?.data?.msg || 'Cannot connect to server.', [
        { text: 'Scan Again', onPress: () => { setScanned(false); setProcessing(false); setStatusMsg(''); } },
        { text: 'Cancel', onPress: onClose },
      ]);
    }
    setProcessing(false);
  };

  if (!visible) return null;

  if (!permission) {
    return (
      <Modal visible={visible} animationType="slide" statusBarTranslucent>
        <View style={styles.center}>
          <ActivityIndicator color="#fff" size="large" />
        </View>
      </Modal>
    );
  }

  if (!permission.granted) {
    return (
      <Modal visible={visible} animationType="slide" statusBarTranslucent>
        <View style={styles.center}>
          <Ionicons name="camera-outline" size={56} color="rgba(255,255,255,0.45)" />
          <Text style={styles.permTitle}>Camera Access Required</Text>
          <Text style={styles.permText}>
            Camera access is needed to scan employee QR codes for attendance.
          </Text>
          <TouchableOpacity style={styles.permBtn} onPress={requestPermission}>
            <Text style={styles.permBtnTxt}>Grant Permission</Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={onClose} style={styles.cancelBtn}>
            <Text style={styles.cancelTxt}>Cancel</Text>
          </TouchableOpacity>
        </View>
      </Modal>
    );
  }

  return (
    <Modal visible={visible} animationType="slide" statusBarTranslucent>
      <View style={styles.container}>
        <CameraView
          style={StyleSheet.absoluteFillObject}
          facing="back"
          barcodeScannerSettings={{ barcodeTypes: ['qr'] }}
          onBarcodeScanned={scanned ? undefined : handleScan}
        />

        {/* Top dark bar */}
        <View style={styles.topBar}>
          <TouchableOpacity onPress={onClose} style={styles.closeBtn}>
            <Ionicons name="close" size={22} color="#fff" />
          </TouchableOpacity>
          <Text style={styles.topTitle}>Attendance Scanner</Text>
          <View style={{ width: 38 }} />
        </View>

        {/* Middle row: dark sides + transparent scan frame */}
        <View style={styles.middleRow}>
          <View style={styles.sideDark} />
          <View style={styles.frame}>
            <View style={[styles.corner, styles.tl]} />
            <View style={[styles.corner, styles.tr]} />
            <View style={[styles.corner, styles.bl]} />
            <View style={[styles.corner, styles.br]} />
            {processing && (
              <View style={styles.processingBox}>
                <ActivityIndicator color="#fff" size="large" />
                <Text style={styles.processingTxt}>{statusMsg || 'Processing…'}</Text>
              </View>
            )}
          </View>
          <View style={styles.sideDark} />
        </View>

        {/* Bottom dark bar */}
        <View style={styles.bottomBar}>
          <Ionicons name="qr-code-outline" size={20} color="rgba(255,255,255,0.65)" />
          <Text style={styles.hintTxt}>
            {processing
              ? statusMsg
              : 'Hold your employee QR code inside the frame'}
          </Text>
        </View>
      </View>
    </Modal>
  );
}

const FRAME = 240;

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#000' },

  center: {
    flex: 1, backgroundColor: '#0f2027',
    justifyContent: 'center', alignItems: 'center', padding: 32,
  },

  topBar: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    backgroundColor: 'rgba(0,0,0,0.65)',
    paddingTop: 56, paddingBottom: 18, paddingHorizontal: 20,
  },
  closeBtn: {
    width: 38, height: 38, borderRadius: 19,
    backgroundColor: 'rgba(255,255,255,0.18)',
    alignItems: 'center', justifyContent: 'center',
  },
  topTitle: { color: '#fff', fontSize: 17, fontWeight: '700' },

  middleRow: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
  },
  sideDark: {
    flex: 1,
    alignSelf: 'stretch',
    backgroundColor: 'rgba(0,0,0,0.55)',
  },
  frame: {
    width: FRAME,
    height: FRAME,
    position: 'relative',
  },
  corner: {
    position: 'absolute', width: 26, height: 26,
    borderColor: '#fff', borderRadius: 3,
  },
  tl: { top: 0, left: 0, borderTopWidth: 3, borderLeftWidth: 3 },
  tr: { top: 0, right: 0, borderTopWidth: 3, borderRightWidth: 3 },
  bl: { bottom: 0, left: 0, borderBottomWidth: 3, borderLeftWidth: 3 },
  br: { bottom: 0, right: 0, borderBottomWidth: 3, borderRightWidth: 3 },

  processingBox: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.72)',
    borderRadius: 4,
    justifyContent: 'center', alignItems: 'center', gap: 12,
  },
  processingTxt: { color: '#fff', fontSize: 13 },

  bottomBar: {
    backgroundColor: 'rgba(0,0,0,0.65)',
    paddingVertical: 28, paddingHorizontal: 24,
    flexDirection: 'row', alignItems: 'center',
    justifyContent: 'center', gap: 10,
  },
  hintTxt: {
    color: 'rgba(255,255,255,0.8)', fontSize: 13,
    textAlign: 'center', flex: 1, lineHeight: 20,
  },

  permTitle: {
    color: '#fff', fontSize: 20, fontWeight: '700',
    marginTop: 20, marginBottom: 10,
  },
  permText: {
    color: 'rgba(255,255,255,0.6)', fontSize: 14,
    textAlign: 'center', marginBottom: 28, lineHeight: 22,
  },
  permBtn: {
    backgroundColor: '#6366f1', borderRadius: 12,
    paddingVertical: 14, paddingHorizontal: 32,
  },
  permBtnTxt: { color: '#fff', fontWeight: '700', fontSize: 15 },
  cancelBtn:  { marginTop: 16, padding: 8 },
  cancelTxt:  { color: 'rgba(255,255,255,0.5)', fontSize: 14 },
});
