CupNavi PWA scaffold. Streamlit's static file scope is not sufficient for a production
service worker controlling the app root. The manifest can be reused by the future
public PWA/Next.js frontend or a reverse proxy that serves service-worker.js at /.
