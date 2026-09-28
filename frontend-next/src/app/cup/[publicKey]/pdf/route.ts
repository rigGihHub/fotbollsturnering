const API_BASE = (
  process.env.CUPNAVI_API_BASE || process.env.NEXT_PUBLIC_CUPNAVI_API_BASE || "http://localhost:8000"
).replace(/\/$/, "");

export async function GET(_request: Request, { params }: { params: Promise<{ publicKey: string }> }) {
  const { publicKey } = await params;
  try {
    const upstream = await fetch(`${API_BASE}/api/public/cups/${encodeURIComponent(publicKey)}/pdf`, {
      cache: "no-store",
      signal: AbortSignal.timeout(60_000),
    });
    if (!upstream.ok) {
      return new Response(upstream.status === 404 ? "Cupen är inte publicerad." : "PDF kunde inte skapas just nu.", {
        status: upstream.status === 404 ? 404 : 503,
        headers: { "Cache-Control": "no-store" },
      });
    }
    if (!upstream.headers.get("content-type")?.includes("application/pdf")) {
      return new Response("Servern skickade inte en PDF-fil.", { status: 502, headers: { "Cache-Control": "no-store" } });
    }
    const content = await upstream.arrayBuffer();
    if (new TextDecoder("ascii").decode(content.slice(0, 5)) !== "%PDF-") {
      return new Response("PDF-filen kunde inte kontrolleras.", { status: 502, headers: { "Cache-Control": "no-store" } });
    }
    return new Response(content, {
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": upstream.headers.get("content-disposition") || "attachment; filename=cupnavi.pdf",
        "Cache-Control": "no-store",
      },
    });
  } catch {
    return new Response("CupNavi kunde inte nå PDF-tjänsten. Försök igen.", { status: 503, headers: { "Cache-Control": "no-store" } });
  }
}
