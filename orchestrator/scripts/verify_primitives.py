"""Verify TỪNG primitive trên GeoGebra applet THẬT (yêu cầu cốt lõi của spec).

Mỗi primitive có một test plan tự chứa. Harness: compile → render qua ggb-service →
kiểm (a) mọi lệnh chạy, (b) output của statement cuối đều DEFINED, (c) mọi assert = 1.
Primitive đạt cả ba ⇒ ghi vào lock file primitives_verified.json. "Verified = đúng mãi."

Chạy (cần ggb-service):
    GGB_SERVICE_URL=http://localhost:8081 ./.venv/Scripts/python -m scripts.verify_primitives
"""
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ggb_client import GgbClient
from app.primitives.registry import PRIMITIVES
from app.primitives.compiler import validate_plan, compile_plan

LOCK = Path(os.path.dirname(os.path.abspath(__file__))) / ".." / "primitives_verified.json"


async def verify_one(client: GgbClient, name: str) -> dict:
    prim = PRIMITIVES[name]
    plan = prim.test
    errs = validate_plan(plan)
    if errs:
        return {"ok": False, "reason": "plan invalid: " + "; ".join(errs)}
    commands, asserts = compile_plan(plan)
    try:
        render = await client.render(commands, ["png"], checks=asserts)
    except Exception as e:
        return {"ok": False, "reason": f"render error: {e}", "commands": commands}

    # (a) lệnh lỗi?
    bad = [s for s in render.get("perCommandStatus", []) if not s.get("ok")]
    # (b) output statement cuối defined?
    last_out = set(plan[-1].get("out", []))
    objs = {o["name"]: o for o in render.get("objects", [])}

    def _is_def(n):
        # tên có thể bị GeoGebra subscript hóa (auxT_1...) — match theo base.
        if n in objs:
            return objs[n].get("defined", False)
        for k, o in objs.items():
            if k.split("_")[0] == n:
                return o.get("defined", False)
        return False

    undefined = [n for n in last_out if not _is_def(n)]
    # (c) asserts
    failed_asserts = [c for c in render.get("checkResults", []) if c.get("value") != 1]

    ok = not bad and not undefined and not failed_asserts
    res = {"ok": ok, "commands": commands, "asserts": asserts}
    if not ok:
        reason = []
        if bad:
            reason.append("lệnh lỗi: " + "; ".join(f"{s['command']}" for s in bad))
        if undefined:
            reason.append("output undefined: " + ", ".join(undefined))
        if failed_asserts:
            reason.append("assert fail: " + "; ".join(f"{c['expr']}={c['value']}" for c in failed_asserts))
        res["reason"] = " | ".join(reason)
    return res


async def main() -> int:
    url = os.environ.get("GGB_SERVICE_URL", "http://localhost:8081")
    client = GgbClient(url)
    verified = {}
    failures = 0
    for name in PRIMITIVES:
        r = await verify_one(client, name)
        mark = "OK " if r["ok"] else "FAIL"
        print(f"[{mark}] {name}")
        if r["ok"]:
            verified[name] = {"commands": r["commands"], "asserts": r["asserts"]}
        else:
            failures += 1
            print(f"        → {r.get('reason')}")
            if r.get("commands"):
                print(f"        cmds: {r['commands']}")

    LOCK.resolve().write_text(json.dumps(verified, ensure_ascii=False, indent=2), encoding="utf-8")
    total = len(PRIMITIVES)
    print(f"\n{total - failures}/{total} primitive verified → khóa vào {LOCK.name}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
