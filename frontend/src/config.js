/**
 * Global Configuration for Bet Legend
 * Auto-detects production vs development environment
 */
const IS_PROD = import.meta.env.PROD;

// In Production (Render), we expect VITE_API_URL to be set to your Render URL
// In Development, we fallback to localhost:8000
export const API_BASE_URL = IS_PROD
    ? (import.meta.env.VITE_API_URL || 'https://betlegend.onrender.com')
    : 'http://localhost:8000';
