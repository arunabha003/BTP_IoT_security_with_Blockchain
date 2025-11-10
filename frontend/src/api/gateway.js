import axios from 'axios';

const API_BASE_URL = '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Status & Root
export const getStatus = () => api.get('/status');
export const getRoot = () => api.get('/root');

// Key Generation
export const generateKeypair = (keyType = 'ed25519') => 
  api.post('/keygen', { keyType });

// Device Enrollment
export const enrollDevice = (publicKeyPEM, keyType = 'ed25519') =>
  api.post('/enroll', { publicKeyPEM, keyType });

// Device Authentication
export const authenticateDevice = (authData) =>
  api.post('/auth', authData);

// Device Revocation
export const revokeDevice = (deviceIdHex) =>
  api.post('/revoke', { deviceIdHex });

// Get Witness
export const getWitness = (deviceIdHex) =>
  api.get(`/witness/${deviceIdHex}`);

// Get All Devices
export const getDevices = (statusFilter = null) => {
  const params = statusFilter ? { status: statusFilter } : {};
  return api.get('/devices', { params });
};

export default api;
