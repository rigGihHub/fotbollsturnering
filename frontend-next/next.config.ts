import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: "standalone",
  poweredByHeader: false,
  async headers(){return [{source:"/:path*",headers:[
    {key:"Content-Security-Policy",value:"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https://quickchart.io https:; connect-src 'self' https://cupnavi-api.onrender.com https://api.open-meteo.com https://geocoding-api.open-meteo.com; font-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"},
    {key:"Strict-Transport-Security",value:"max-age=31536000; includeSubDomains"},
    {key:"X-Content-Type-Options",value:"nosniff"},{key:"X-Frame-Options",value:"DENY"},
    {key:"Referrer-Policy",value:"strict-origin-when-cross-origin"},
    {key:"Permissions-Policy",value:"camera=(), microphone=(), geolocation=(), payment=()"},
  ]}]},
};

export default nextConfig;
