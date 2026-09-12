const configured = process.env.NEXT_PUBLIC_CUPNAVI_API_BASE?.trim();

export const CLIENT_API_BASE = (
  configured && /^https?:\/\//i.test(configured)
    ? configured
    : process.env.NODE_ENV === "production"
      ? "https://cupnavi-api.onrender.com"
      : "http://localhost:8000"
).replace(/\/$/, "");
