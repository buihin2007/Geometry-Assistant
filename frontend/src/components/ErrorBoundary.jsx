import React from "react";

// Chặn "màn hình đen": một lỗi render/effect bất kỳ ở cây con sẽ bị bắt ở đây và
// hiện thông báo thân thiện + nút tải lại, thay vì React gỡ sạch DOM (chỉ còn nền tối).
export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    // Log để xem trong console (và để hook giám sát nếu có sau này).
    console.error("[ErrorBoundary]", error, info?.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{
          minHeight: "100vh", display: "grid", placeItems: "center",
          background: "#0f1117", color: "#e6e8ee", padding: 24,
          fontFamily: "system-ui, sans-serif", textAlign: "center",
        }}>
          <div style={{ maxWidth: 480 }}>
            <h2 style={{ marginBottom: 8 }}>Ứng dụng gặp sự cố hiển thị 😢</h2>
            <p style={{ color: "#9aa3b2", lineHeight: 1.6 }}>
              Có thể trình duyệt chưa tải được thư viện vẽ hình (GeoGebra) — thường do
              mạng chậm hoặc bị chặn. Hãy thử tải lại trang, hoặc đổi mạng/trình duyệt.
            </p>
            <button
              onClick={() => window.location.reload()}
              style={{
                marginTop: 14, cursor: "pointer", border: "1px solid #4f8cff",
                background: "#4f8cff", color: "#fff", borderRadius: 9,
                padding: "10px 18px", fontSize: 14, fontWeight: 600,
              }}
            >
              Tải lại trang
            </button>
            <pre style={{
              marginTop: 16, fontSize: 11, color: "#6b7280", whiteSpace: "pre-wrap",
            }}>{String(this.state.error?.message || this.state.error)}</pre>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
