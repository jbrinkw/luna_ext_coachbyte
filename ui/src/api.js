// API base path for CoachByte backend.
// Default assumes Caddy routes /api/coachbyte/* to the backend service,
// but it can be overridden for local development or remote testing by
// setting VITE_COACHBYTE_API_BASE.
const envBase =
  (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_COACHBYTE_API_BASE) ||
  '';

export const API_BASE = envBase
  ? envBase.replace(/\/+$/, '')
  : '/api/coachbyte';
