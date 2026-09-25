#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""District Vision 시착 매장 두 곳을 도쿄 플랜에 추가한다."""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import enrich as E  # noqa: E402

DATA = ROOT / "data.json"
data = json.loads(DATA.read_text(encoding="utf-8"))
regions = {region["id"]: region for region in data["regions"]}


def add_or_replace(region_id, name, desc, query, badge="District Vision"):
    shops = regions[region_id]["shops"]
    shops[:] = [shop for shop in shops if shop["name"] != name]
    shop = {"name": name, "desc": desc, "hours": "미확인", "addr": "", "badge": badge}
    center = (regions[region_id].get("lat"), regions[region_id].get("lng"))
    E.enrich_into(shop, query, center, "s-" + E.slug(name))
    shops.append(shop)


add_or_replace(
    "harajuku",
    "blinc vase",
    "District Vision 시착 · Keiichi 렌즈 변경 / Mami / Koharu 후보 · 모델·D+ 렌즈 재고를 먼저 전화 확인",
    "blinc vase 北青山 3-5-16",
)
add_or_replace(
    "daikanyama",
    "Continuer Ebisu",
    "District Vision 시착 · Koharu 등 신상품/재입고 확인 매장 · 에비스미나미, 모델·D+ 렌즈 재고를 먼저 전화 확인",
    "Continuer 恵比寿南 2-9-2",
)

DATA.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("DONE: blinc vase, Continuer Ebisu")
