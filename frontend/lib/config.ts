// API configuration
export const API_URL = process.env.NEXT_PUBLIC_API_BASE_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Storage keys
export const STORAGE_KEYS = {
  USER_TOKEN: "momentum:user-token",
  API_KEY: "momentum:api-key",
} as const;
