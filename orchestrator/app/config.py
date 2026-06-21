from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Đọc .env ở thư mục cha (monorepo root) lẫn local.
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"), env_file_encoding="utf-8", extra="ignore"
    )

    # ----- LLM chung (PLAN §4.1 / §13) -----
    llm_provider: str = "mock"
    llm_api_key: str = ""
    llm_model: str = "gemini-2.5-flash"

    # Tách provider tùy chọn (để trống = fallback về llm_*)
    generator_provider: str = ""
    generator_model: str = ""
    generator_api_key: str = ""
    reviewer_provider: str = ""
    reviewer_model: str = ""
    reviewer_api_key: str = ""

    enable_review: bool = True
    max_fix_rounds: int = 3
    max_llm_calls_per_request: int = 8
    # Hai tầng model (upgrade_plan §4): planner mặc định (Haiku) fail verify sau hết
    # vòng sửa → thử lại bằng model mạnh hơn (Sonnet) MỘT lượt. Chỉ bài khó mới tốn.
    planner_escalation_model: str = "claude-sonnet-4-6"
    escalate_on_verify_fail: bool = True
    # Kiến trúc planner+compiler (THCS_construction_library_spec). Tắt → dùng
    # Generator sinh lệnh thô (pipeline cũ) cho mọi đề.
    use_planner: bool = True
    # Tách bước "phân tích đề" cho đề nhiều mệnh đề phụ thuộc (PLAN Vấn đề 3).
    enable_analysis: bool = True
    # Ghi log đề fail để xây bộ test hồi quy dần (PLAN Vấn đề 3).
    fail_log_path: str = "logs/failed_problems.jsonl"
    # Report do NGƯỜI DÙNG gửi (bắt lỗi im lặng auto-log không thấy). Lưu plan text,
    # KHÔNG lưu ảnh. Prod cần DB bền (xem DEPLOY.md) vì file mất khi scale-to-zero.
    report_log_path: str = "logs/reports.jsonl"

    # ----- Supabase -----
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    # ----- Services -----
    ggb_service_url: str = "http://localhost:8081"
    orchestrator_port: int = 8080

    # ----- Demo gating -----
    demo_limit_per_ip: int = 2

    # ----- Provider resolution helpers -----
    def generator_cfg(self) -> tuple[str, str, str]:
        provider = self.generator_provider or self.llm_provider
        model = self.generator_model or self.llm_model
        key = self.generator_api_key or self.llm_api_key
        return provider, model, key

    def reviewer_cfg(self) -> tuple[str, str, str]:
        provider = self.reviewer_provider or self.llm_provider
        model = self.reviewer_model or self.llm_model
        key = self.reviewer_api_key or self.llm_api_key
        return provider, model, key

    def escalation_cfg(self) -> tuple[str, str, str]:
        # Cùng provider/key planner, đổi sang model mạnh hơn.
        provider, _, key = self.generator_cfg()
        return provider, self.planner_escalation_model, key


@lru_cache
def get_settings() -> Settings:
    return Settings()
