import React, { useState, useEffect } from 'react';
import {
  View, Text, Modal, StyleSheet, TouchableOpacity, ActivityIndicator, Alert,
} from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera';
import * as Location from 'expo-location';
import { Ionicons } from '@expo/vector-icons';
import { employeeCheckin } from '../api/client';

export default function AttendanceScannerModal({ visible, onClose, onSuccess }) {
  const [camPermission, requestCamPermission] = useCameraPermissions();
  const [scanned, setScanned]     = useState(false);
  const [processing, setProcessing] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');
  const [locationReady, setLocationReady] = useState(false);
  const [coords, setCoords]       = useState(null);
  const [locError, setLocError]   = useState(null);

  useEffect(() => {
    if (visible) {
      setScanned(false);
      setProcessing(false);
      setStatusMsg('');
      setLocationReady(false);
      setCoords(null);
      setLocError(null);
      fetchLocation();
    }
  }, [visible]);

  const fetchLocation = async () => {
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        setLocError('Location permission denied. Please enable location to mark attendance.');
        return;
      }
      const loc = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.High,
      });
      setCoords({ lat: loc.coords.latitude, lon: loc.coords.longitude });
      setLocationReady(true);
    } catch {
      setLocError('Could not get your location. Please check GPS and try again.');
    }
  };

  const handleScan = async ({ data }) => {
    if (scanned || processing || !locationReady) return;
    setScanned(true);
    setProcessing(true);
    setStatusMsg('Marking attendance…');
    try {
      const res = await employeeCheckin(coords.lat, coords.lon);
      if (res.data.ok) {
        const action = res.data.action;
        const title =
          action === 'login'   ? '✅ Checked In'   :
          action === 'logout'  ? '✅ Checked Out'  : '✅ Re-Logged In';
        Alert.alert(title, `${res.data.status}\nTime: ${res.data.time}`, [
          { text: 'OK', onPress: () => { onSuccess && onSuccess(res.data); onClose(); } },
        ]);
      } else {
        Alert.alert('Cannot Mark Attendance', res.data.msg || 'Something went wrong.', [
          { text: 'Try Again', onPress: () => { setScanned(false); setProcessing(false); setStatusMsg(''); } },
          { text: 'Cancel', onPress: onClose },
        ]);
      }
    } catch (e) {
      Alert.alert('Error', e.response?.data?.msg || 'Cannot connect to server.', [
        { text: 'Try Again', onPress: () => { setScanned(false); setProcessing(false); setStatusMsg(''); } },
        { text: 'Cancel', onPress: onClose },
      ]);
    }
    setProcessing(false);
  };

  if (!visible) return null;

  /* ── Location error ── */
  if (locError) {
    return (
      <Modal visible={visible} animationType="slide" statusBarTranslucent>
        <View style={styles.center}>
          <Ionicons name="location-outline" size={56} color="rgba(255,255,255,0.45)" />
          <Text style={styles.permTitle}>Location Required</Text>
          <Text style={styles.permText}>{locError}</Text>
          <TouchableOpacity style={styles.permBtn} onPress={fetchLocation}>
            <Text style={styles.permBtnTxt}>Retry</Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={onClose} style={styles.cancelBtn}>
            <Text style={styles.cancelTxt}>Cancel</Text>
          </TouchableOpacity>
        </View>
      </Modal>
    );
  }

  /* ── Getting location ── */
  if (!locationReady) {
    return (
      <Modal visible={visible} animationType="slide" statusBarTranslucent>
        <View style={styles.center}>
          <ActivityIndicator color="#fff" size="large" />
          <Text style={styles.loadingTxt}>Getting your location…</Text>
          <TouchableOpacity onPress={onClose} style={styles.cancelBtn}>
            <Text style={styles.cancelTxt}>Cancel</Text>
          </TouchableOpacity>
        </View>
      </Modal>
    );
  }

  /* ── Camera permission loading ── */
  if (!camPermission) {
    return (
      <Modal visible={visible} animationType="slide" statusBarTranslucent>
        <View style={styles.center}><ActivityIndicator color="#fff" size="large" /></View>
      </Modal>
    );
  }

  /* ── Camera permission denied ── */
  if (!camPermission.granted) {
    return (
      <Modal visible={visible} animationType="slide" statusBarTranslucent>
        <View style={styles.center}>
          <Ionicons name="camera-outline" size={56} color="rgba(255,255,255,0.45)" />
          <Text style={styles.permTitle}>Camera Access Required</Text>
          <Text style={styles.permText}>Camera is needed to scan the attendance QR code.</Text>
          <TouchableOpacity style={styles.permBtn} onPress={requestCamPermission}>
            <Text style={styles.permBtnTxt}>Grant Camera Access</Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={onClose} style={styles.cancelBtn}>
            <Text style={styles.cancelTxt}>Cancel</Text>
          </TouchableOpacity>
        </View>
      </Modal>
    );
  }

  /* ── Scanner ── */
  return (
    <Modal visible={visible} animationType="slide" statusBarTranslucent>
      <View style={styles.container}>
        <CameraView
          style={StyleSheet.absoluteFillObject}
          facing="back"
          barcodeScannerSettings={{ barcodeTypes: ['qr'] }}
          onBarcodeScanned={scanned ? undefined : handleScan}
        />

        {/* Header */}
        <View style={styles.topBar}>
          <TouchableOpacity onPress={onClose} style={styles.closeBtn}>
            <Ionicons name="close" size={22} color="#fff" />
          </TouchableOpacity>
          <Text style={styles.topTitle}>Attendance Scanner</Text>
          <View style={{ width: 38 }} />
        </View>

        {/* Scan frame */}
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
                <Text style={styles.processingTxt}>{statusMsg}</Text>
              </View>
            )}
          </View>
          <View style={styles.sideDark} />
        </View>

        {/* Footer */}
        <View style={styles.bottomBar}>
          <View style={styles.locBadge}>
            <Ionicons name="location" size={14} color="#22C55E" />
            <Text style={styles.locTxt}>Location captured</Text>
          </View>
          <Text style={styles.hintTxt}>
            {processing ? statusMsg : 'Scan your employee QR code to mark attendance'}
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

  loadingTxt: {
    color: 'rgba(255,255,255,0.7)', fontSize: 15, marginTop: 16,
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

  middleRow: { flex: 1, flexDirection: 'row', alignItems: 'center' },
  sideDark:  { flex: 1, alignSelf: 'stretch', backgroundColor: 'rgba(0,0,0,0.55)' },

  frame: { width: FRAME, height: FRAME, position: 'relative' },
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
    backgroundColor: 'rgba(0,0,0,0.72)', borderRadius: 4,
    justifyContent: 'center', alignItems: 'center', gap: 12,
  },
  processingTxt: { color: '#fff', fontSize: 13 },

  bottomBar: {
    backgroundColor: 'rgba(0,0,0,0.65)',
    paddingVertical: 28, paddingHorizontal: 24,
    alignItems: 'center', gap: 10,
  },
  locBadge: {
    flexDirection: 'row', alignItems: 'center', gap: 6,
    backgroundColor: 'rgba(34,197,94,0.18)',
    paddingHorizontal: 12, paddingVertical: 6, borderRadius: 20,
  },
  locTxt:  { color: '#22C55E', fontSize: 12, fontWeight: '700' },
  hintTxt: { color: 'rgba(255,255,255,0.8)', fontSize: 13, textAlign: 'center', lineHeight: 20 },

  permTitle: { color: '#fff', fontSize: 20, fontWeight: '700', marginTop: 20, marginBottom: 10, textAlign: 'center' },
  permText:  { color: 'rgba(255,255,255,0.6)', fontSize: 14, textAlign: 'center', marginBottom: 28, lineHeight: 22 },
  permBtn:   { backgroundColor: '#173B8C', borderRadius: 12, paddingVertical: 14, paddingHorizontal: 32 },
  permBtnTxt:{ color: '#fff', fontWeight: '700', fontSize: 15 },
  cancelBtn: { marginTop: 16, padding: 8 },
  cancelTxt: { color: 'rgba(255,255,255,0.5)', fontSize: 14 },
});
