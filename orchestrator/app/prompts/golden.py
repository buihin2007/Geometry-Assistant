# Golden example set (PLAN §11) — few-shot grounding + bộ test hồi quy.
# Mỗi mục: problem → {commands, asserts}. CẢNH BÁO: phải verify trên GeoGebra thật.
# Đã verify qua ggb-service: VD1–VD4 (cũ) + tiếp tuyến + 3 đường cao (aux-hide).

GOLDEN = [
    {
        "problem": "Vẽ tam giác ABC, kẻ đường cao AH xuống BC.",
        "commands": [
            "A=(0,0)",
            "B=(6,0)",
            "C=(1.5,4.5)",
            "tri=Polygon(A,B,C)",
            "aux_h=PerpendicularLine(A,Line(B,C))",
            "H=Intersect(aux_h,Line(B,C))",
            "AH=Segment(A,H)",
        ],
        "asserts": ["ArePerpendicular(aux_h,Line(B,C))"],
    },
    {
        "problem": "Vẽ tam giác ABC có ba đường cao, xác định trực tâm H.",
        # Mỗi đường cao: aux đường vuông góc (TỰ ẨN) → chân đường cao → đoạn hữu hạn.
        "commands": [
            "A=(0,0)",
            "B=(6,0)",
            "C=(2,5)",
            "tri=Polygon(A,B,C)",
            "aux_a=PerpendicularLine(A,Line(B,C))",
            "aux_b=PerpendicularLine(B,Line(A,C))",
            "aux_c=PerpendicularLine(C,Line(A,B))",
            "Ha=Intersect(aux_a,Line(B,C))",
            "Hb=Intersect(aux_b,Line(A,C))",
            "Hc=Intersect(aux_c,Line(A,B))",
            "ha=Segment(A,Ha)",
            "hb=Segment(B,Hb)",
            "hc=Segment(C,Hc)",
            "H=Intersect(aux_a,aux_b)",
        ],
        "asserts": ["AreConcurrent(aux_a,aux_b,aux_c)"],
    },
    {
        "problem": "Tam giác ABC nội tiếp đường tròn tâm O.",
        "commands": [
            "A=(0,0)",
            "B=(6,0)",
            "C=(2,5)",
            "tri=Polygon(A,B,C)",
            "circ=Circle(A,B,C)",
            "O=Center(circ)",
        ],
        "asserts": ["AreEqual(Distance(A,O),Radius(circ))"],
    },
    {
        "problem": "Tam giác ABC với đường tròn nội tiếp tâm I.",
        "commands": [
            "A=(0,0)",
            "B=(6,0)",
            "C=(2,5)",
            "tri=Polygon(A,B,C)",
            "aux_bi1=AngleBisector(B,A,C)",
            "aux_bi2=AngleBisector(A,B,C)",
            "I=Intersect(aux_bi1,aux_bi2)",
            "r=Distance(I,Line(A,B))",
            "incirc=Circle(I,r)",
        ],
        "asserts": ["IsTangent(Line(A,B),incirc)"],
    },
    {
        "problem": "Vẽ ba trung tuyến của tam giác ABC, xác định trọng tâm G.",
        "commands": [
            "A=(0,0)",
            "B=(6,0)",
            "C=(2,5)",
            "tri=Polygon(A,B,C)",
            "Ma=Midpoint(B,C)",
            "Mb=Midpoint(A,C)",
            "Mc=Midpoint(A,B)",
            "med_a=Segment(A,Ma)",
            "med_b=Segment(B,Mb)",
            "med_c=Segment(C,Mc)",
            "G=Centroid(tri)",
        ],
        "asserts": ["AreCollinear(A,G,Ma)"],
    },
    {
        "problem": "Cho đường tròn (O), từ điểm A ngoài đường tròn kẻ hai tiếp tuyến AB và AC (B, C là tiếp điểm).",
        "commands": [
            "O=(0,0)",
            "circ=Circle(O,3)",
            "A=(8,1)",
            "auxT=Tangent(A,circ)",
            "B=Intersect(auxT_1,circ)",
            "C=Intersect(auxT_2,circ)",
            "tAB=Segment(A,B)",
            "tAC=Segment(A,C)",
        ],
        "asserts": ["IsTangent(auxT_1,circ)", "IsTangent(auxT_2,circ)"],
    },
    {
        # Biến thể diễn đạt "vuông góc / hạ đường vuông góc" + nhiều bước phụ thuộc.
        "problem": "Cho tam giác ABC. Gọi M là trung điểm BC. Từ M hạ đường vuông góc xuống AB tại điểm K.",
        "commands": [
            "A=(0,0)",
            "B=(6,0)",
            "C=(3,5)",
            "tri=Polygon(A,B,C)",
            "M=Midpoint(B,C)",
            "aux_mk=PerpendicularLine(M,Line(A,B))",
            "K=Intersect(aux_mk,Line(A,B))",
            "MK=Segment(M,K)",
        ],
        "asserts": ["ArePerpendicular(aux_mk,Line(A,B))"],
    },
    {
        # Đường kính + tiếp tuyến tại đầu mút (vuông góc bán kính).
        "problem": "Cho đường tròn (O) đường kính AB. Vẽ tiếp tuyến của đường tròn tại A.",
        "commands": [
            "O=(0,0)",
            "circ=Circle(O,3)",
            "A=(-3,0)",
            "B=(3,0)",
            "AB=Segment(A,B)",
            "auxt=PerpendicularLine(A,Line(O,A))",
            "P=Point(auxt)",
            "tanA=Segment(A,P)",
        ],
        "asserts": ["IsTangent(auxt,circ)"],
    },
]


def format_fewshot() -> str:
    import json

    blocks = []
    for ex in GOLDEN:
        out = json.dumps(
            {"commands": ex["commands"], "asserts": ex.get("asserts", [])},
            ensure_ascii=False,
        )
        blocks.append(f'Đề: "{ex["problem"]}"\nKết quả: {out}')
    return "\n\n".join(blocks)
