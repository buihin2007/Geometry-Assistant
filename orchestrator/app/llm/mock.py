import json
from .base import LLMProvider

# Provider giả lập để chạy/test offline khi chưa có API key.
# Generator: trả lệnh dựng tam giác ABC mặc định + cố khớp vài từ khóa đề.
# Reviewer: luôn pass.


class MockProvider(LLMProvider):
    async def complete_text(self, system: str, user: str) -> str:
        text = user.lower()
        asserts: list[str] = []
        # Đề tiếp tuyến: dựng đúng bằng Tangent + ẩn aux + assert IsTangent.
        if "tiếp tuyến" in text or "tiep tuyen" in text:
            commands = [
                "O=(0,0)",
                "circ=Circle(O,3)",
                "A=(8,1)",
                "auxT=Tangent(A,circ)",
                "B=Intersect(auxT_1,circ)",
                "C=Intersect(auxT_2,circ)",
                "tAB=Segment(A,B)",
                "tAC=Segment(A,C)",
            ]
            asserts = ["IsTangent(auxT_1,circ)", "IsTangent(auxT_2,circ)"]
            return json.dumps({"commands": commands, "asserts": asserts}, ensure_ascii=False)

        commands = ["A=(0,0)", "B=(6,0)", "C=(2,5)", "tri=Polygon(A,B,C)"]
        if "đường cao" in text or "duong cao" in text:
            commands += [
                "aux_h=PerpendicularLine(A,Line(B,C))",
                "H=Intersect(aux_h,Line(B,C))",
                "AH=Segment(A,H)",
            ]
            asserts.append("ArePerpendicular(aux_h,Line(B,C))")
        if "ngoại tiếp" in text or "ngoai tiep" in text or "nội tiếp đường tròn" in text:
            commands += ["circ=Circle(A,B,C)", "O=Center(circ)"]
            asserts.append("AreEqual(Distance(A,O),Radius(circ))")
        if "trung tuyến" in text or "trọng tâm" in text:
            commands += ["Ma=Midpoint(B,C)", "med=Segment(A,Ma)", "G=Centroid(tri)"]
        return json.dumps({"commands": commands, "asserts": asserts}, ensure_ascii=False)

    async def complete_vision(self, system: str, user: str, png_base64: str) -> str:
        return json.dumps({"status": "pass", "suggestions": []}, ensure_ascii=False)
