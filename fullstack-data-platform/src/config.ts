const rawBase = String(import.meta.env.VITE_API_BASE_URL || '').trim();
let apiBase = rawBase || '/api';
// If a host/root was provided (e.g. http://localhost:8000) ensure we append /api
if (!apiBase.endsWith('/api')) {
  apiBase = apiBase.replace(/\/+$/, '');
  apiBase = apiBase + '/api';
}

export const CONFIG = {
  // Resolved API base (always ends with /api)
  API_BASE_URL: apiBase,
  // Detects if running locally (npm run dev) vs production build
  IS_DEV: import.meta.env.DEV,
  // Client-side developer shortcuts removed for production builds.
  // The name of the super-admin group in Cognito/Entra ID
  ADMIN_GROUP: import.meta.env.VITE_ADMIN_GROUP || 'Admin',
};
