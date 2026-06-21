import json
import time
from pathlib import Path
from dataclasses import dataclass, field
from .config import Settings
from .ggb_client import GgbClient
from .llm.factory import make_provider
from .agents.generator import Generator, is_complex
from .agents.planner import Planner
from .agents.validator import validate
from .agents.geometry_verify import verify_relations
from .agents.reviewer import Reviewer
from .primitives.compiler import validate_plan, compile_plan


@dataclass
class PipelineResult:
    commands: list[str]
    png_base64: str | None
    svg: str | None = None
    ggb_base64: str | None = None
    rounds: int = 0
    llm_calls: int = 0
    review_passed: bool | None = None
    verified: bool = False  # validator OK và review pass/disabled → coi như đạt
    warnings: list[str] = field(default_factory=list)
    log: list[str] = field(default_factory=list)


class LLMBudgetExceeded(Exception):
    pass


class Pipeline:
    """Điều phối Generator → Validator → Reviewer với vòng sửa (PLAN §5)."""

    def __init__(self, settings: Settings):
        self.s = settings
        self.ggb = GgbClient(settings.ggb_service_url)

        gprov, gmodel, gkey = settings.generator_cfg()
        rprov, rmodel, rkey = settings.reviewer_cfg()
        self.generator = Generator(make_provider(gprov, gmodel, gkey))
        self.planner = Planner(make_provider(gprov, gmodel, gkey))
        self.reviewer = Reviewer(make_provider(rprov, rmodel, rkey))

        # Planner tầng cao (Sonnet) — chỉ dựng nếu bật escalation (upgrade_plan §4).
        self._escalation_planner = None
        if settings.escalate_on_verify_fail:
            eprov, emodel, ekey = settings.escalation_cfg()
            if ekey:
                self._escalation_planner = Planner(make_provider(eprov, emodel, ekey))

    async def run(self, problem: str, formats: list[str] | None = None) -> PipelineResult:
        formats = formats or ["png"]
        # Cần png để review nhìn; thêm nếu thiếu (sẽ lọc lại khi trả nếu muốn).
        render_formats = list({*formats, "png"})

        # Lượt 1: planner mặc định (Haiku). Fail verify + bật escalation → lượt 2 (Sonnet).
        res = await self._attempt(problem, render_formats, self.planner)
        if (not res.verified and self.s.use_planner and self._escalation_planner is not None):
            res.log.append(
                f"[escalate] lượt Haiku chưa đạt verify → thử lại bằng {self.s.planner_escalation_model}"
            )
            res2 = await self._attempt(problem, render_formats, self._escalation_planner)
            res2.log = res.log + ["[escalate] ─── lượt model mạnh ───"] + res2.log
            if res2.verified or res2.png_base64:
                res = res2

        # Ghi log đề chưa hoàn hảo (còn cảnh báo / review chưa đạt) để mở rộng test
        # hồi quy dần (PLAN Vấn đề 3) — không chặn, lỗi ghi log thì bỏ qua.
        if res.warnings or res.review_passed is False:
            self._log_failure(problem, res)
        return res

    async def _attempt(
        self, problem: str, render_formats: list[str], planner: Planner
    ) -> PipelineResult:
        res = PipelineResult(commands=[], png_base64=None)
        commands: list[str] = []
        feedback: str | None = None

        # Chế độ sinh: "planner" (DSL→compiler tất định) hoặc "generator" (lệnh thô,
        # escape hatch). RAW hoặc planner hỏng nhiều lần → tự rớt về generator.
        mode = "planner" if self.s.use_planner else "generator"
        prev_plan: list | None = None

        # --- Bước phân tích đề (chỉ cho đề phức tạp, 1 lời gọi LLM) — PLAN Vấn đề 3 ---
        analysis: str | None = None
        if self.s.enable_analysis and mode == "generator" and is_complex(problem):
            try:
                self._charge_llm(res)
                analysis = await self.generator.analyze(problem)
                res.log.append("[analyze] đề phức tạp → đã phân tích đối tượng trước")
            except Exception as e:
                res.log.append(f"[analyze] bỏ qua (lỗi): {e}")

        max_rounds = self.s.max_fix_rounds
        # round 0 = sinh lần đầu; round 1..max = các vòng sửa.
        for round_idx in range(max_rounds + 1):
            res.rounds = round_idx

            # --- Sinh lệnh: planner→compiler (tất định) hoặc generator (thô) ---
            if mode == "planner":
                self._charge_llm(res)
                try:
                    plan = await planner.plan(problem, feedback=feedback, prev_plan=prev_plan)
                except Exception as e:
                    res.log.append(f"[round {round_idx}] planner lỗi → escape generator: {e}")
                    mode = "generator"
                    feedback = None
                    continue
                if Planner.is_raw(plan):
                    res.log.append(f"[round {round_idx}] planner RAW → escape generator")
                    mode = "generator"
                    feedback = None
                    continue
                plan_errs = validate_plan(plan)
                if plan_errs:
                    prev_plan = plan
                    feedback = "Plan sai luật, sửa lại:\n" + "\n".join(f"- {e}" for e in plan_errs)
                    res.log.append(f"[round {round_idx}] plan invalid: {len(plan_errs)} lỗi")
                    if round_idx == max_rounds:
                        res.log.append("[escape] plan vẫn sai sau hết vòng → generator")
                        mode = "generator"
                    continue
                prev_plan = plan
                commands, asserts = compile_plan(plan)
                res.log.append(
                    f"[round {round_idx}] planner→compiler: {len(plan)} bước → "
                    f"{len(commands)} lệnh, {len(asserts)} assert"
                )
            else:
                self._charge_llm(res)
                commands, asserts = await self.generator.generate(
                    problem, previous=commands or None, feedback=feedback, analysis=analysis
                )
                res.log.append(
                    f"[round {round_idx}] generator → {len(commands)} lệnh, {len(asserts)} assert"
                )
            res.commands = commands

            # --- Render (không tốn LLM) — kèm asserts để kiểm quan hệ đề nêu tên ---
            render = await self.ggb.render(commands, render_formats, checks=asserts)
            res.png_base64 = render.get("pngBase64")
            res.svg = render.get("svg")
            res.ggb_base64 = render.get("ggbBase64")

            # --- Verifier quan hệ Python (đọc tọa độ) là PHÁN QUYẾT CHÍNH; GeoGebra
            #     chỉ fallback cho assert Python chưa kết luận (upgrade_plan §5). Không
            #     loại oan hình đúng: Python trả None → giữ kết quả GeoGebra. ---
            if asserts:
                py = verify_relations(asserts, render.get("objects", []))
                n_py, n_disagree = 0, 0
                for chk in render.get("checkResults", []) or []:
                    v = py.get(chk.get("expr"))
                    if v is None:
                        continue
                    n_py += 1
                    ggb = chk.get("value")
                    if ggb is not None and (ggb == 1) != bool(v):
                        n_disagree += 1
                    chk["value"] = 1 if v else 0  # Python authoritative
                if n_py:
                    res.log.append(
                        f"[round {round_idx}] verify Python: {n_py}/{len(asserts)} assert "
                        f"(còn lại fallback GeoGebra); bất đồng với GeoGebra: {n_disagree}"
                    )

            # --- Technical Validator (deterministic) ---
            vr = validate(commands, render)
            if not vr.ok:
                feedback = "Lỗi kỹ thuật khi dựng hình:\n" + vr.feedback_text()
                res.log.append(f"[round {round_idx}] validator FAIL: {len(vr.errors)} lỗi")
                if round_idx == max_rounds:
                    res.warnings.append(
                        "Hết vòng sửa nhưng vẫn còn lỗi kỹ thuật: " + vr.feedback_text()
                    )
                    break
                continue
            res.log.append(f"[round {round_idx}] validator OK")

            # --- Cảnh báo "làm gọn hình" (nét thừa): non-blocking, thử sửa 1 vòng ---
            if vr.warnings and round_idx < max_rounds:
                feedback = "Làm gọn hình (cảnh báo, không bắt buộc nhưng nên sửa):\n" + "\n".join(
                    f"- {w}" for w in vr.warnings
                )
                res.log.append(f"[round {round_idx}] cleanup warnings: {len(vr.warnings)}")
                continue
            if vr.warnings:
                res.warnings.extend(vr.warnings)

            # --- Reviewer (LLM vision, có thể tắt) ---
            if not self.s.enable_review or not res.png_base64:
                res.review_passed = None
                res.verified = True  # validator đã OK; không review thì coi như đạt
                break

            self._charge_llm(res)
            try:
                review = await self.reviewer.review(problem, res.png_base64)
            except Exception as e:
                # Review lỗi (vd Gemini 429, provider down) KHÔNG được làm hỏng
                # cả request — hình đã dựng hợp lệ, cứ trả về kèm cảnh báo.
                res.review_passed = None
                res.verified = True  # technical OK; chỉ vision provider lỗi
                res.warnings.append(f"Bỏ qua review (lỗi provider): {e}")
                res.log.append(f"[round {round_idx}] reviewer SKIPPED: {e}")
                break
            if review.passed:
                res.review_passed = True
                res.verified = True
                res.log.append(f"[round {round_idx}] reviewer PASS")
                break

            res.review_passed = False
            feedback = "Gợi ý từ người soát hình:\n" + review.feedback_text()
            res.log.append(f"[round {round_idx}] reviewer REVISE: {len(review.suggestions)} gợi ý")
            if round_idx == max_rounds:
                res.warnings.append("Hết vòng sửa, review vẫn chưa đạt hoàn toàn.")
                break

        return res

        return res

    def _log_failure(self, problem: str, res: PipelineResult) -> None:
        try:
            path = Path(self.s.fail_log_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            entry = {
                "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "problem": problem,
                "commands": res.commands,
                "review_passed": res.review_passed,
                "warnings": res.warnings,
            }
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def _charge_llm(self, res: PipelineResult) -> None:
        # Trần chi phí cứng (PLAN §5 / §13) — chặn request lỗi lặp nuốt quota.
        if res.llm_calls >= self.s.max_llm_calls_per_request:
            raise LLMBudgetExceeded(
                f"Vượt MAX_LLM_CALLS_PER_REQUEST={self.s.max_llm_calls_per_request}"
            )
        res.llm_calls += 1
