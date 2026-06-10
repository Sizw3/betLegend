/**
 * Global Configuration for Bet Legend
 * Auto-detects production vs development environment
 */
const IS_PROD = import.meta.env.PROD;

// In Production (Vercel), we expect VITE_API_URL to be set to your Render/Fly.io URL
// In Development, we fallback to localhost:8000
export const API_BASE_URL = IS_PROD
    ? (import.meta.env.VITE_API_URL || 'https://your-production-backend.com')
    : 'http://localhost:8000';
