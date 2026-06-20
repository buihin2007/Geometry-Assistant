import asyncio, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.ggb_client import GgbClient
from app.primitives.compiler import validate_plan, compile_plan
from app.agents.validator import validate

def s(op,args,out): return {"op":op,"args":args,"out":out}
PLANS = {
 "T03 đường cao": [s("point_free",{"x":0,"y":0},["A"]),s("point_free",{"x":6,"y":0},["B"]),
    s("point_free",{"x":2,"y":5},["C"]),s("triangle",{"A":"A","B":"B","C":"C"},["tri"]),
    s("altitude",{"vertex":"A","A":"A","B":"B","C":"C"},["H","AH"])],
 "C05 hai tiếp tuyến": [s("point_free",{"x":0,"y":0},["O"]),s("circle_center_radius",{"O":"O","r":3},["circ"]),
    s("point_free",{"x":8,"y":1},["A"]),s("tangent_from_point",{"P":"A","c":"circ"},["B","C","tAB","tAC"])],
 "Q03 hình vuông": [s("point_free",{"x":0,"y":0},["A"]),s("point_free",{"x":4,"y":0},["B"]),
    s("square",{"A":"A","B":"B"},["C","D","poly"])],
 "C08 nửa đường tròn": [s("point_free",{"x":-5,"y":0},["M"]),s("point_free",{"x":5,"y":0},["N"]),
    s("semicircle",{"M":"M","N":"N"},["s","O"])],
 "X01 nửa đtròn nhiều bước": [s("point_free",{"x":-5,"y":0},["M"]),s("point_free",{"x":5,"y":0},["N"]),
    s("semicircle",{"M":"M","N":"N"},["s","O"]),s("point_on_segment",{"A":"M","B":"O","t":0.35},["P"]),
    s("line",{"A":"M","B":"N"},["MN"]),s("perpendicular_through",{"P":"P","line":"MN"},["d"]),
    s("intersect_line_circle",{"line":"d","c":"s","index":1},["Q"]),s("segment",{"A":"P","B":"Q"},["PQ"])],
}
async def main():
    c=GgbClient(os.environ.get("GGB_SERVICE_URL","http://localhost:8081"))
    for name,plan in PLANS.items():
        errs=validate_plan(plan)
        if errs: print(f"FAIL  {name}: plan invalid {errs}",flush=True); continue
        cmds,asr=compile_plan(plan)
        r=await c.render(cmds,["png"],checks=asr)
        v=validate(cmds,r)
        chk=" ".join(f"{x['expr']}={x['value']}" for x in r.get("checkResults",[]))
        st="PASS" if (v.ok and r.get("pngBase64")) else "FAIL"
        print(f"{st}  {name}  | steps={len(plan)} cmds={len(cmds)} | asserts: {chk or '—'} | warn={v.warnings} err={v.errors}",flush=True)
asyncio.run(main())
