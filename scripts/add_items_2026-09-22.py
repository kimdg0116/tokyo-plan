#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""도쿄 플랜에 새 항목 추가 — 하드쉘·시계·District Vision, 보트슈즈 제거."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path.home() / "Desktop/app/tokyo-plan/scripts"))
import enrich as E  # noqa: E402  (재사용: enrich_into, search 등)

DATA = pathlib.Path.home() / "Desktop/app/tokyo-plan/data.json"
data = json.loads(DATA.read_text(encoding="utf-8"))
regions_by_id = {r["id"]: r for r in data["regions"]}


def shop(name, desc, badge=None):
    d = {"name": name, "desc": desc, "hours": "미확인", "addr": ""}
    if badge:
        d["badge"] = badge
    return d


def add_shop(region_id, s):
    regions_by_id[region_id]["shops"].append(s)


# ---------------------------------------------------------------- 1) 보트슈즈 제거
before = len(data["bonus"])
data["bonus"] = [b for b in data["bonus"] if "보트슈즈" not in b["name"]]
print("bonus 제거:", before, "->", len(data["bonus"]))

# ---------------------------------------------------------------- 2) 하드쉘 + District Vision (전부 새 shop, enrich_into 로 실측)
NEW = [
    ("shibuya", shop("and wander MIYASHITA PARK", "겨울 등반 하드쉘 · Pertex Shield 20,000mm", badge="하드쉘"),
     "and wander MIYASHITA PARK South 渋谷"),
    ("shibuya", shop("Kith Tokyo", "District Vision 취급 (공식 스톡리스트) · 재고는 매장 확인", badge="District Vision"),
     "Kith Tokyo MIYASHITA PARK North"),
    ("harajuku", shop("Patagonia 시부야점", "겨울 등반 하드쉘 · Storm Racer 2.5L", badge="하드쉘"),
     "パタゴニア 渋谷 神宮前"),
    ("kanda", shop("Arc'teryx 간다점", "겨울 등반 하드쉘 · Norvan SL GORE-TEX ShakeDry", badge="하드쉘"),
     "アークテリクス 神田店"),
    ("kanda", shop("Teton Bros (사카이야 스포츠)", "겨울 등반 하드쉘 · 셸재킷 라인 취급", badge="하드쉘"),
     "サカイヤスポーツ 神保町"),
    ("shinjuku", shop("Rab (이시이스포츠 요도바시신주쿠니시구치점)", "겨울 등반 하드쉘 · Phantom Mountain 2.5L", badge="하드쉘"),
     "石井スポーツ 新宿ヨドバシ西口店"),
]
for region_id, s, query in NEW:
    center = (regions_by_id[region_id].get("lat"), regions_by_id[region_id].get("lng"))
    E.enrich_into(s, query + " 東京", center, "s-" + E.slug(s["name"]))
    add_shop(region_id, s)

# ---------------------------------------------------------------- 3) 시계 브랜드 — 몽벨처럼 brand 등록
watchnian_main = shop("Watchnian 신주쿠본점", "빈티지 시계 · 신주쿠·시부야·긴자 5개 지점 중 하나", badge="시계")
E.enrich_into(watchnian_main, "Watchnian 新宿本店 新宿区新宿", (regions_by_id["shinjuku"]["lat"], regions_by_id["shinjuku"]["lng"]), "s-" + E.slug(watchnian_main["name"]))
add_shop("shinjuku", watchnian_main)
watchnian_main["brand"] = "watchnian"

firekids_main = shop("Fire Kids 긴자나인점", "빈티지 시계 · 나카노 안 가도 되는 대체 지점", badge="시계")
E.enrich_into(firekids_main, "Fire Kids 銀座ナイン 中央区銀座", (regions_by_id["ginza"]["lat"], regions_by_id["ginza"]["lng"]), "s-" + E.slug(firekids_main["name"]))
add_shop("ginza", firekids_main)
firekids_main["brand"] = "firekids"

BRAND_EXTRA = {
    "watchnian": [
        {"label": "시부야점", "q": "Watchnian 渋谷"},
        {"label": "긴자5초메점", "q": "Watchnian 銀座5丁目"},
        {"label": "긴자2초메점", "q": "Watchnian 銀座2丁目"},
        {"label": "긴자본점", "q": "Watchnian 銀座本店"},
        {"label": "나카노점", "q": "Watchnian 中野ブロードウェイ"},
    ],
    "firekids": [
        {"label": "나카노 브로드웨이점", "q": "Fire Kids 中野ブロードウェイ"},
        {"label": "요코하마본점", "q": "Fire Kids 横浜本店"},
    ],
}
brands_out = data.setdefault("brands", {})
for bid, name, main_region, main_shop in [
    ("watchnian", "Watchnian", "shinjuku", watchnian_main),
    ("firekids", "Fire Kids", "ginza", firekids_main),
]:
    locations = [{"label": regions_by_id[main_region]["name"], "regionId": main_region, "shopName": main_shop["name"]}]
    for ex in BRAND_EXTRA[bid]:
        loc = {"label": ex["label"]}
        E.enrich_into(loc, ex["q"] + " 東京", None, "b-" + bid + "-" + E.slug(ex["label"]))
        locations.append(loc)
    brands_out[bid] = {"name": name, "locations": locations}

DATA.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
print("DONE")
