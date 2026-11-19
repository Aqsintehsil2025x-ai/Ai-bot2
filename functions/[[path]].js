const ORIGIN = "https://ai-bot-2--aqsintehsil2025.replit.app";

export async function onRequest(context) {
  const incoming = new URL(context.request.url);
  const path = incoming.pathname;
  const isBackendRoute =
    path === "/auth" ||
    path.startsWith("/auth/") ||
    path.startsWith("/xfa/api/") ||
    path === "/api/stats";

  if (!isBackendRoute) return context.next();

  const target = new URL(path + incoming.search, ORIGIN);
  const headers = new Headers(context.request.headers);
  headers.set("x-forwarded-host", incoming.host);
  headers.set("x-forwarded-proto", incoming.protocol.slice(0, -1));
  headers.delete("host");

  const upstreamRequest = new Request(target.toString(), {
    method: context.request.method,
    headers,
    body: ["GET", "HEAD"].includes(context.request.method) ? undefined : context.request.body,
    redirect: "manual",
  });

  try {
    const upstream = await fetch(upstreamRequest);
    const responseHeaders = new Headers(upstream.headers);
    responseHeaders.set("cache-control", "no-store");
    responseHeaders.delete("content-length");
    return new Response(upstream.body, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: responseHeaders,
    });
  } catch {
    return Response.json(
      { error: "XFA backend bağlantısı şu anda kurulamadı." },
      { status: 502, headers: { "cache-control": "no-store" } },
    );
  }
}
