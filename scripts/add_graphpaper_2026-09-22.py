"""Graphpaper 도쿄 직영점 2곳을 일정 데이터에 추가한다.

공식 스토어 정보(2026-09-22 확인):
https://asia.graphpaper-tokyo.com/pages/concept
"""

import json
from pathlib import Path

import enrich as E


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data.json"


def weekly_hours(closed_day):
    return [
        {"day": day, "time": "휴무" if day == closed_day else "12:00~19:00", "off": day == closed_day}
        for day in ("월", "화", "수", "목", "금", "토", "일")
    ]


def replace_or_insert(shops, shop, after_name):
    shops[:] = [item for item in shops if item["name"] != shop["name"]]
    position = next((i + 1 for i, item in enumerate(shops) if item["name"] == after_name), len(shops))
    shops.insert(position, shop)


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    aoyama_hours = weekly_hours("월")
    tokyo_hours = weekly_hours("수")

    aoyama = {
        "name": "Graphpaper AOYAMA",
        "desc": "내 옷 · 도쿄 직영 · 미니멀 데일리웨어",
        "hours": aoyama_hours,
        "addr": "〒150-0001 東京都渋谷区神宮前５丁目３６−６ KARI MANSION 1A/2D",
        "brand": "graphpaper",
    }
    E.enrich_into(
        aoyama,
        "Graphpaper AOYAMA 東京都渋谷区神宮前5-36-6",
        (35.6702, 139.7027),
        "s-graphpaper-aoyama",
        keep_addr=aoyama["addr"],
        keep_hours=aoyama_hours,
    )
    # 영업일·주소는 Google Places보다 공식 스토어 페이지 값을 우선한다.
    aoyama["addr"] = "〒150-0001 東京都渋谷区神宮前５丁目３６−６ KARI MANSION 1A/2D"
    aoyama["hours"] = aoyama_hours

    tokyo = {
        "label": "요요기 · 니시산도",
        "addr": "〒151-0053 東京都渋谷区代々木３丁目３８−１０ Nishi-Sando Mansion 2F",
        "hours": tokyo_hours,
    }
    E.enrich_into(
        tokyo,
        "Graphpaper TOKYO 東京都渋谷区代々木3-38-10",
        (35.682, 139.696),
        "b-graphpaper-tokyo",
        keep_addr=tokyo["addr"],
        keep_hours=tokyo_hours,
    )
    tokyo["addr"] = "〒151-0053 東京都渋谷区代々木３丁目３８−１０ Nishi-Sando Mansion 2F"
    tokyo["hours"] = tokyo_hours

    harajuku = next(region for region in data["regions"] if region["id"] == "harajuku")
    replace_or_insert(harajuku["shops"], aoyama, "Goldwin Harajuku")

    data.setdefault("brands", {})["graphpaper"] = {
        "name": "Graphpaper",
        "locations": [
            {"label": "하라주쿠 · 아오야마", "regionId": "harajuku", "shopName": "Graphpaper AOYAMA"},
            tokyo,
        ],
    }

    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
