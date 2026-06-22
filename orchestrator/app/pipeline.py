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
from .agents.geometry_verify import verify_relations, check_constraints
from .agents.constraint_repair import repair_distance_constraints
from .agents.quad_repair import reorder_crossed_quads
from .agents.orient import apply_orientation
from .agents.reviewer import Reviewer
from .primitives.compiler import (
    validate_plan, compile_plan, valid_prefix, extract_constraints, extract_orient,
)


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
    partial: bool = False   # chỉ dựng được một phần (fail gọn §6)
    warnings: list[str] = field(default_factory=list)
    log: list[str] = field(default_factory=list)
    last_plan: list | None = None  # plan planner gần nhất (để dựng phần hợp lệ khi fail)


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

        # --- Fail gọn (upgrade_plan §6): nếu vẫn chưa đạt VÀ nguyên nhân là có BƯỚC
        #     KHÔNG DỰNG ĐƯỢC (vượt phạm vi / thiếu primitive / RAW), trả phần dựng được
        #     (có nhãn) + báo bước fail, thay vì hình vỡ/trống. ---
        if not res.verified and res.last_plan:
            prefix, bad = valid_prefix(res.last_plan)
            if bad is not None and prefix:
                try:
                    cmds, asserts = compile_plan(prefix)
                    render = await self.ggb.render(cmds, render_formats, checks=[])
                    if render.get("pngBase64"):
                        res.commands = cmds
                        res.png_base64 = render.get("pngBase64")
                        res.svg = render.get("svg")
                        res.ggb_base64 = render.get("ggbBase64")
                        res.partial = True
                        res.warnings.insert(0, f"Chỉ dựng được một phần hình: chưa dựng được {bad}.")
                        res.log.append(f"[partial] dựng {len(prefix)}/{len(res.last_plan)} bước; dừng tại: {bad}")
                except Exception as e:
                    res.log.append(f"[partial] không dựng được phần hợp lệ: {e}")

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

        # --- Bước phân tích đề thành bảng đối tượng cho ĐỀ PHỨC TẠP (1 lời gọi LLM,
        #     upgrade_plan §3). Dùng cho CẢ planner (tiêm làm khung phân rã) lẫn generator. ---
        analysis: str | None = None
        if self.s.enable_analysis and is_complex(problem):
            try:
                self._charge_llm(res)
                analysis = await self.generator.analyze(problem)
                res.log.append("[analyze] đề phức tạp → đã phân tích cấu trúc đối tượng trước")
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
                    plan = await planner.plan(
                        problem, feedback=feedback, prev_plan=prev_plan, analysis=analysis
                    )
                except Exception as e:
                    res.log.append(f"[round {round_idx}] planner lỗi → escape generator: {e}")
                    mode = "generator"
                    feedback = None
                    continue
                res.last_plan = plan  # giữ plan gần nhất (kể cả RAW/sai) cho fail gọn §6
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
                constraints = extract_constraints(plan)  # ràng buộc "sao cho"
                orient = extract_orient(plan)  # gợi ý định hướng base/apex
                res.log.append(
                    f"[round {round_idx}] planner→compiler: {len(plan)} bước → "
                    f"{len(commands)} lệnh, {len(asserts)} assert, {len(constraints)} ràng buộc"
                )
            else:
                self._charge_llm(res)
                commands, asserts = await self.generator.generate(
                    problem, previous=commands or None, feedback=feedback, analysis=analysis
                )
                constraints = []
                orient = None
                res.log.append(
                    f"[round {round_idx}] generator → {len(commands)} lệnh, {len(asserts)} assert"
                )
            res.commands = commands

            # --- Render (không tốn LLM) — kèm asserts để kiểm quan hệ đề nêu tên ---
            render = await self.ggb.render(commands, render_formats, checks=asserts)
            self._apply_python_relations(render, asserts)

            # --- Sửa TẤT ĐỊNH thứ tự đỉnh tứ giác bị bắt chéo (gán lại tọa độ 4 nhãn
            #     theo vòng quanh) — không phụ thuộc planner/LLM. ---
            rq, qchanged = reorder_crossed_quads(commands, render.get("objects", []))
            if qchanged:
                commands = rq
                res.commands = commands
                render = await self.ggb.render(commands, render_formats, checks=asserts)
                self._apply_python_relations(render, asserts)
                res.log.append(f"[round {round_idx}] sửa thứ tự đỉnh tứ giác (bắt chéo)")

            # --- Ràng buộc "sao cho" (bất đẳng thức/thứ tự): verify từ tọa độ; nếu vi
            #     phạm, SỬA CƠ HỌC (tất định) rồi render lại — ưu tiên trước khi tốn LLM. ---
            con_errors: list[str] = []
            if constraints:
                bad = [c for c in check_constraints(constraints, render.get("objects", [])) if c["ok"] is False]
                if bad:
                    new_cmds, changed = repair_distance_constraints(commands, bad, render.get("objects", []))
                    if changed:
                        commands = new_cmds
                        res.commands = commands
                        render = await self.ggb.render(commands, render_formats, checks=asserts)
                        self._apply_python_relations(render, asserts)
                        bad = [c for c in check_constraints(constraints, render.get("objects", [])) if c["ok"] is False]
                        res.log.append(f"[round {round_idx}] sửa cơ học ràng buộc → còn vi phạm: {len(bad)}")
                    for c in bad:
                        con_errors.append(
                            f"Ràng buộc {c['lhs']} {c['rel']} {c['rhs']} CHƯA thỏa "
                            f"(đo được {c['lv']:.2f} vs {c['rv']:.2f}). Đặt điểm vào vùng thỏa điều kiện."
                        )

            # --- ĐỊNH HƯỚNG TỔNG QUÁT: xoay base về ngang-dưới, lật apex lên trên (phép
            #     biến hình CỨNG, giữ nguyên quan hệ). Chỉ khi planner gắn role base/apex. ---
            if orient and not con_errors:
                ot = apply_orientation(commands, orient["base"], orient["apex"], render.get("objects", []))
                if ot != commands:
                    commands = ot
                    res.commands = commands
                    render = await self.ggb.render(commands, render_formats, checks=asserts)
                    self._apply_python_relations(render, asserts)
                    res.log.append(f"[round {round_idx}] định hướng lại (base ngang dưới, apex trên)")

            res.png_base64 = render.get("pngBase64")
            res.svg = render.get("svg")
            res.ggb_base64 = render.get("ggbBase64")

            # --- Technical Validator (deterministic) + ràng buộc "sao cho" ---
            vr = validate(commands, render)
            if con_errors:
                vr.errors.extend(con_errors)
                vr.ok = False
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

    def _apply_python_relations(self, render: dict, asserts: list[str]) -> None:
        """Verifier quan hệ Python (đọc tọa độ) là PHÁN QUYẾT CHÍNH; GeoGebra fallback
        cho assert Python chưa kết luận (upgrade_plan §5). Ghi đè checkResults tại chỗ."""
        if not asserts:
            return
        py = verify_relations(asserts, render.get("objects", []))
        for chk in render.get("checkResults", []) or []:
            v = py.get(chk.get("expr"))
            if v is not None:
                chk["value"] = 1 if v else 0

    def _charge_llm(self, res: PipelineResult) -> None:
        # Trần chi phí cứng (PLAN §5 / §13) — chặn request lỗi lặp nuốt quota.
        if res.llm_calls >= self.s.max_llm_calls_per_request:
            raise LLMBudgetExceeded(
                f"Vượt MAX_LLM_CALLS_PER_REQUEST={self.s.max_llm_calls_per_request}"
            )
        res.llm_calls += 1
