// Proxy tài nguyên GeoGebra qua chính domain Cloudflare Pages.
// Lý do: client ở VN tải engine GeoGebra trực tiếp từ www.geogebra.org bị chậm/chặn
// → applet treo mãi. Cloudflare edge (có PoP tại VN) tải hộ từ geogebra.org ở phía
// server, trình duyệt chỉ nói chuyện với domain của ta (không bị chặn). Engine được
// version-pin (vd /ggb/apps/5.4.920.0/...) nên cache rất hiệu quả.
//
// /ggb/<path>  →  https://www.geogebra.org/<path>
export async function onRequest({ params, request, waitUntil }) {
  const parts = params.path;
  const path = Array.isArray(parts) ? parts.join("/") : parts || "";
  const src = new URL(request.url);
  const target = "https://www.geogebra.org/" + path + src.search;

  const cache = caches.default;
  const cacheKey = new Request(target, { method: "GET" });
  let resp = await cache.match(cacheKey);
  if (resp) return resp;

  const upstream = await fetch(target, { redirect: "follow" });
  resp = new Response(upstream.body, upstream);
  resp.headers.set("Access-Control-Allow-Origin", "*");
  // Tài nguyên engine bất biến theo version → cache dài ở edge lẫn trình duyệt.
  resp.headers.set("Cache-Control", "public, max-age=86400, s-maxage=604800");
  if (upstream.status === 200) waitUntil(cache.put(cacheKey, resp.clone()));
  return resp;
}
