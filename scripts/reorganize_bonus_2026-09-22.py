#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""여유 탭 정리 — 가게·관광지 삭제, 사진은 해당 지역 목록으로 이동 + 15번 노트의 로컬 스폿 추가."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path.home() / "Desktop/app/tokyo-plan/scripts"))
import enrich as E  # noqa: E402

DATA = pathlib.Path.home() / "Desktop/app/tokyo-plan/data.json"
data = json.loads(DATA.read_text(encoding="utf-8"))
regions_by_id = {r["id"]: r for r in data["regions"]}


def spot(name, tip, time=None):
    d = {"name": name, "tip": tip, "cost": "0"}
    if time:
        d["time"] = time
    return d


# ---------------------------------------------------------------- 기존 bonus 「사진」 항목 → 지역으로 재배치
RELOCATE = [
    ("ikebukuro-night", spot("도덴 아라카와선 (사쿠라 트램)",
        "도쿄에 하나 남은 노면전차. 민가 사이를 지난다. 숙소 1정거장(오츠카)에서 탄다.", time="낮")),
    ("ueno", spot("야네센 (야나카·네즈·센다기)",
        "공습을 피한 동네. 유야케단단 계단·고양이·네즈 신사 붉은 토리이 터널. 35mm 화각의 교과서. 우에노에서 한 정거장.", time="낮 · 반나절")),
    ("ginza", spot("츠키지 장외시장",
        "사람·불·김·해산물 — 움직이는 피사체가 가장 많은 곳. 긴자 축 시작 전 아침에 붙인다.", time="오전 (14시 마감)")),
    ("shinjuku", spot("오모이데요코초 · 골든가이",
        "꼬치 연기 + 붉은 등 + 좁은 골목. 도쿄 밤의 표준 이미지. ⚠️ 촬영금지 표시 많음 — 골목 전경만, 가게 안은 허락받고.", time="밤")),
    ("asakusa", spot("짓켄바시(十間橋)",
        "강물에 스카이트리가 통째로 반영되는 유일한 다리. 오시아게 도보 15분.", time="밤 · 무풍일 때")),
    ("daikanyama", spot("나카메구로 메구로강",
        "강변 + 편집숍. 다이칸야마에서 1정거장.", time="저녁~밤")),
    ("shinjuku", spot("도쿄도청 프로젝션 매핑",
        "청사 벽면 전체를 쓰는 무료 상영. 숙소 5분. 매일(악천후 제외) 17:30~21:30 사이 여러 작품 연속 상영, 자유 입퇴장.", time="17:30~21:30")),
    # 15번 노트 — 로컬 골목 중 살짝 벗어나도 되는 것
    ("ikebukuro-night", spot("카구라자카",
        "돌바닥 좁은 골목(효고요코초)·요정·프랑스인 거리. 비 오면 최고. 숙소에서 유라쿠초선 8분.", time="저녁")),
    ("ikebukuro-night", spot("아카바네 이치반가이",
        "낮술 동네. 오래된 이자카야 간판과 사람. 관광객이 거의 없다. 숙소에서 10분.", time="낮술 시간대")),
]

for region_id, sp in RELOCATE:
    regions_by_id[region_id].setdefault("photoSpots", []).append(sp)
    center = (regions_by_id[region_id].get("lat"), regions_by_id[region_id].get("lng"))
    q = sp["name"].split("(")[0].split("·")[0].strip()
    E.enrich_into(sp, q + " 東京", None, "p-" + E.slug(sp["name"]))

# ---------------------------------------------------------------- bonus 정리 — 가게·관광지 삭제, 사진은 이미 옮겼으니 전부 비운다
data["bonus"] = []

DATA.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
print("DONE — bonus cleared, relocated", len(RELOCATE), "photo spots")
