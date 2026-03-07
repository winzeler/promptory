// Runtime config — overwritten at deploy time by deploy-web.sh
// For local dev, VITE_API_BASE_URL (empty string) proxies via vite.config.ts
window.__PROMPTDIS_CONFIG__ = {
  API_BASE_URL: "",
};
