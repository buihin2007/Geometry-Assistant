const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8080";

async function jsonOrThrow(res) {
  let data = null;
  try {
    data = await res.json();
  } catch (e) {}
  if (!res.ok) {
    const msg = (data && data.detail) || `Lỗi ${res.status}`;
    const err = new Error(msg);
    err.status = res.status;
    throw err;
  }
  return data;
}

export async function generate(problem, formats, token) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API_URL}/generate`, {
    method: "POST",
    headers,
    body: JSON.stringify({ problem, formats }),
  });
  return jsonOrThrow(res);
}

export async function listFigures(token) {
  const res = await fetch(`${API_URL}/figures`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return jsonOrThrow(res);
}

export async function saveFigure(figure, token) {
  const res = await fetch(`${API_URL}/figures`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(figure),
  });
  return jsonOrThrow(res);
}

export async function deleteFigure(id, token) {
  const res = await fetch(`${API_URL}/figures/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  return jsonOrThrow(res);
}

export async function sendReport(report) {
  const res = await fetch(`${API_URL}/report`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(report),
  });
  return jsonOrThrow(res);
}

export async function health() {
  const res = await fetch(`${API_URL}/health`);
  return jsonOrThrow(res);
}
