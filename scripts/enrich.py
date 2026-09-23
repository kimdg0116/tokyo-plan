#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""도쿄 플랜 데이터 보강 — 구글 Places로 위치·영업시간·사진·지도링크를 한 번에.
가게(대표 1곳 + 다른 지점) · 사진 · 숙소 전부 이걸로 채운다.
영업시간은 요일별 한 줄씩([{day,time}, …] 월~일 고정 순서)이 이런 앱들의 표준 형식이다.
"""
import json
import math
import pathlib
import re
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data.json"
PHOTOS = ROOT / "photos"
KEY_FILE = pathlib.Path.home() / ".config" / "tokyo-food" / "google_places.key"
ENDPOINT = "https://places.googleapis.com/v1/places:searchText"
FIELDS = ",".join([
    "places.id", "places.displayName", "places.formattedAddress", "places.location",
    "places.regularOpeningHours.weekdayDescriptions", "places.googleMapsUri", "places.photos",
])
DAY_KO = {"Monday": "월", "Tuesday": "화", "Wednesday": "수", "Thursday": "목",
          "Friday": "금", "Saturday": "토", "Sunday": "일",
          "月曜日": "월", "火曜日": "화", "水曜日": "수", "木曜日": "목",
          "金曜日": "금", "土曜日": "토", "日曜日": "일"}

api_key = KEY_FILE.read_text(encoding="utf-8").strip()
PHOTOS.mkdir(parents=True, exist_ok=True)


def slug(s):
    s = re.sub(r"[^a-zA-Z0-9가-힣]+", "-", s).strip("-").lower()
    return s[:44] or "x"


DAY_ORDER = ["월", "화", "수", "목", "금", "토", "일"]


def to_korean_hours(descs):
    """구글 weekdayDescriptions → 요일별 한 줄씩 [{day, time, off?}, …] (월~일 고정 순서).
    이 형식이 이런 종류 앱(맛집·여행 플랜)의 영업시간 표준 — 가로로 이어붙이지 않고
    요일마다 줄을 하나씩 쓴다. 프론트는 hoursHtml() 로 그대로 세로 나열한다."""
    by_day = {}
    for d in descs or []:
        day, _, rest = d.partition(": ")
        day_ko = DAY_KO.get(day.strip(), day.strip())
        rest = (rest.replace("時", ":").replace("分", "").replace("～", "~")
                    .replace("定休日", "휴무").replace("休み", "휴무")
                    .replace("24 時間営業", "24시간").replace("Closed", "휴무")
                    .replace("Open 24 hours", "24시간").strip())
        by_day[day_ko] = rest
    if not by_day:
        return None
    rows = []
    for d in DAY_ORDER:
        if d not in by_day:
            continue
        t = by_day[d]
        rows.append({"day": d, "time": t, "off": True} if "휴무" in t else {"day": d, "time": t})
    return rows or None


def search(query, center=None, radius=3000.0):
    body = {"textQuery": query, "languageCode": "ja", "regionCode": "JP", "maxResultCount": 1}
    if center:
        body["locationBias"] = {"circle": {"center": {"latitude": center[0], "longitude": center[1]}, "radius": radius}}
    req = urllib.request.Request(
        ENDPOINT, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "X-Goog-Api-Key": api_key, "X-Goog-FieldMask": FIELDS})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                places = json.load(r).get("places", [])
                return places[0] if places else None
        except urllib.error.HTTPError as e:
            body_txt = e.read().decode("utf-8", "replace")[:200]
            if e.code == 429 and attempt < 2:
                time.sleep(3)
                continue
            print("   ! HTTP", e.code, body_txt)
            return None
        except Exception as e:
            print("   ! err", e)
            return None
    return None


def fetch_photo(place, fname_base):
    existing = list(PHOTOS.glob(fname_base + ".*"))
    if existing:
        return "photos/" + existing[0].name
    photos = place.get("photos") or []
    if not photos:
        return None
    name = photos[0]["name"]
    url = f"https://places.googleapis.com/v1/{name}/media?maxWidthPx=640&key={api_key}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=20) as r:
            ctype = r.headers.get_content_type()
            ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}.get(ctype, ".jpg")
            fname = fname_base + ext
            (PHOTOS / fname).write_bytes(r.read())
            return "photos/" + fname
    except Exception as e:
        print("   ! photo err", e)
        return None


def enrich_into(target, query, center, fname_base, keep_addr=None, keep_hours=None):
    """target dict에 addr/hours/lat/lng/map/photo 채운다. 실패해도 조용히 넘어간다."""
    place = search(query, center)
    if not place:
        print("  MISS", query)
        return False
    loc = place.get("location") or {}
    addr = place.get("formattedAddress")
    hours = to_korean_hours((place.get("regularOpeningHours") or {}).get("weekdayDescriptions"))
    if addr:
        target["addr"] = addr
    elif keep_addr:
        target.setdefault("addr", keep_addr)
    if hours:
        target["hours"] = hours
    elif isinstance(keep_hours, list):
        target.setdefault("hours", keep_hours)   # 이미 구조화된 값이면 유지, 문자열 시절 값은 버린다
    if loc.get("latitude") is not None:
        target["lat"] = loc["latitude"]
        target["lng"] = loc["longitude"]
    if place.get("googleMapsUri"):
        target["map"] = place["googleMapsUri"]
    photo = fetch_photo(place, fname_base)
    if photo:
        target["photo"] = photo
    print("  ok  ", query, "->", addr or "(주소없음)")
    return True



def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))

    # ---------------------------------------------------------------- 숙소
    print("== 숙소 ==")
    hotel = {"name": "도미인 PREMIUM 이케부쿠로", "desc": "체크인 15:00 · 대욕장 15:00~익일 10:00"}
    enrich_into(hotel, "ドーミーインPREMIUM池袋", (35.7295, 139.7109), "hotel-dormyinn-ikebukuro")
    data["hotel"] = hotel
    time.sleep(0.3)

    # ---------------------------------------------------------------- 브랜드 레지스트리
    # 이미 일정 안에 있는 가게는 (region_id, shop_name)로 링크만 한다 (API 호출 없음).
    # extra는 일정엔 없는 다른 지점 — 새로 검색해서 채운다.
    BRANDS = {
        "yamaya": {"name": "야마야", "members": [("shinjuku", "야마야 신주쿠점"),
                                                    ("shibuya", "야마야 시부야 도겐자카우에점"),
                                                    ("ikebukuro-night", "야마야 이케부쿠로 東점"),
                                                    ("ikebukuro-night", "야마야 이케부쿠로 西점"),
                                                    ("ginza", "야마야 긴자점")], "extra": []},
        "shinanoya": {"name": "시나노야", "members": [("shinjuku", "시나노야 신주쿠점"),
                                                       ("shibuya", "시나노야 도겐자카점"),
                                                       ("ikebukuro-night", "시나노야 이케부쿠로점"),
                                                       ("ginza", "시나노야 긴자점")], "extra": []},
        "goldwin": {"name": "Goldwin", "members": [("harajuku", "Goldwin Harajuku")],
                    "extra": [{"label": "마루노우치", "q": "ゴールドウィン 丸の内"}]},
        "deus": {"name": "Deus Ex Machina", "members": [("harajuku", "Deus Ex Machina 하라주쿠")],
                 "extra": [{"label": "시부야", "q": "Deus Ex Machina 渋谷"},
                           {"label": "아사쿠사", "q": "Deus Ex Machina 浅草"}]},
        "chrome-hearts": {"name": "Chrome Hearts", "members": [("harajuku", "Chrome Hearts 아오야마")],
                           "extra": [{"label": "긴자", "q": "クロムハーツ 銀座"},
                                     {"label": "하라주쿠", "q": "クロムハーツ 原宿"}]},
        "adidas-originals": {"name": "adidas Originals", "members": [("harajuku", "아디다스 오리지널스 플래그십"), ("shibuya", "아디다스 브랜드센터 시부야")],
                              "extra": [{"label": "미야시타파크", "q": "アディダス 原宿 宮下パーク"},
                                        {"label": "신주쿠", "q": "アディダス 新宿"}]},
        "united-arrows": {"name": "유나이티드 애로우", "members": [("shibuya", "유나이티드 애로우")],
                           "extra": [{"label": "하라주쿠", "q": "ユナイテッドアローズ 原宿本店"},
                                     {"label": "신주쿠 루미네", "q": "ユナイテッドアローズ ルミネ新宿"}]},
        "montbell": {"name": "몽벨", "members": [("shibuya", "몽벨 시부야")],
                     "extra": [{"label": "신주쿠 남구", "q": "モンベル 新宿南口"},
                               {"label": "오카치마치", "q": "モンベル 御徒町"},
                               {"label": "교바시", "q": "モンベル 京橋"},
                               {"label": "이케부쿠로 도부", "q": "モンベル 東武百貨店 池袋"}]},
        "rinkan": {"name": "RINKAN (크롬하츠 리셀)", "members": [("shibuya", "RINKAN 시부야점")],
                   "extra": [{"label": "신주쿠", "q": "リンカン 新宿店 中古"},
                             {"label": "하라주쿠 silver", "q": "リンカン 原宿 silver"}]},
        "randa": {"name": "RANDA", "members": [("shibuya", "RANDA 시부야")],
                  "extra": [{"label": "루미네에스트 신주쿠", "q": "RANDA ルミネエスト新宿"}]},
        "allu": {"name": "ALLU", "members": [("ginza", "ALLU 긴자")],
                 "extra": [{"label": "신주쿠", "q": "ALLU 新宿店"}]},
        "kindal": {"name": "Kindal", "members": [("shibuya", "Kindal 시부야"), ("ginza", "Kindal 긴자")], "extra": []},
        "bape": {"name": "BAPE", "members": [("harajuku", "BAPE STORE 하라주쿠"), ("harajuku", "BAPE THINK"), ("shibuya", "BAPE STORE 시부야")], "extra": []},
        "japan-blue": {"name": "JAPAN BLUE JEANS", "members": [("harajuku", "JAPAN BLUE JEANS (시부야점 표기)"), ("ueno", "JAPAN BLUE JEANS 우에노점")], "extra": []},
        "nanamica": {"name": "nanamica / PURPLE LABEL", "members": [("daikanyama", "nanamica MOUNTAIN"), ("daikanyama", "nanamica DAIKANYAMA"), ("daikanyama", "nanamica D.W.S.")], "extra": []},
        "deal-design": {"name": "Deal Design", "members": [("ikebukuro-night", "Deal Design 파르코점")],
                         "extra": [{"label": "신주쿠", "q": "ディールデザイン 新宿"},
                                   {"label": "하라주쿠", "q": "ディールデザイン 原宿"}]},
    }

    regions_by_id = {r["id"]: r for r in data["regions"]}


    def find_shop(region_id, name):
        for s in regions_by_id[region_id].get("shops", []):
            if s["name"] == name:
                return s
        return None


    print("\n== 브랜드 extra 지점 ==")
    brands_out = {}
    for bid, b in BRANDS.items():
        locations = []
        # 1) 일정에 이미 있는 멤버 — 링크만 (주소/시간은 그 가게 항목을 그대로 쓴다, 이미 채워져 있거나 아래 shop enrich 단계에서 채워짐)
        for region_id, shop_name in b["members"]:
            s = find_shop(region_id, shop_name)
            if s is None:
                print(f"  ! {bid}: {region_id}/{shop_name} 못 찾음")
                continue
            s["brand"] = bid
            locations.append({"label": regions_by_id[region_id]["name"], "regionId": region_id, "shopName": shop_name})
        # 2) extra — 새로 검색
        for ex in b["extra"]:
            loc_entry = {"label": ex["label"]}
            enrich_into(loc_entry, ex["q"], None, "b-" + bid + "-" + slug(ex["label"]))
            locations.append(loc_entry)
            time.sleep(0.25)
        brands_out[bid] = {"name": b["name"], "locations": locations}
    data["brands"] = brands_out

    # ---------------------------------------------------------------- 가게 본체 (대표 1곳) 전부 새로고침
    print("\n== 가게 본체 ==")
    SKIP_SHOPS = {
        "드럭스토어", "다이소 · Can do · Standard Product · Lakole · Kaldi · Right on",
        "바카라 2곳", "주류 전문점 (야마야 등)", "스포츠용품 거리", "MUJI 긴자", "유니클로 긴자",
    }
    for r in data["regions"]:
        center = (r.get("lat"), r.get("lng"))
        for s in r.get("shops", []):
            if s["name"] in SKIP_SHOPS:
                continue
            q = re.sub(r"[⭐⚠️()（）]", "", s["name"]).strip()
            enrich_into(s, q + " 東京", center, "s-" + slug(s["name"]),
                        keep_addr=s.get("addr"), keep_hours=s.get("hours"))
            time.sleep(0.2)

    # ---------------------------------------------------------------- 사진 (구 "사진 스폿")
    # 지도에 위치도 찍어야 하니 가게와 같은 enrich_into 로 — 좌표·주소·사진 다 받는다
    print("\n== 사진 ==")
    for r in data["regions"]:
        center = (r.get("lat"), r.get("lng"))
        for sp in r.get("photoSpots", []):
            q = re.sub(r"[⭐⚠️()（）]", "", sp["name"]).strip()
            enrich_into(sp, q + " 東京", center, "p-" + slug(sp["name"]))
            time.sleep(0.2)

    # ---------------------------------------------------------------- 다른 지점 중 우리 일정 지역과 가까운 것
    # 일정에 없는 "다른 지점"이 다른 날 어차피 가는 지역 도보권이면, 그 지역 상세에도 참고로 띄운다.
    NEAR_THRESHOLD_M = 1000.0


    def dist_m(a, b):
        R = 6371000
        dlat, dlng = math.radians(b[0] - a[0]), math.radians(b[1] - a[1])
        x = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(a[0])) * math.cos(math.radians(b[0])) * math.sin(dlng / 2) ** 2)
        return 2 * R * math.asin(math.sqrt(x))


    print("\n== 도보권 지역 매칭 ==")
    for b in data["brands"].values():
        for loc in b["locations"]:
            if loc.get("regionId") or loc.get("lat") is None:
                continue
            best = None
            for r in data["regions"]:
                if r.get("lat") is None:
                    continue
                dm = dist_m((loc["lat"], loc["lng"]), (r["lat"], r["lng"]))
                if dm <= NEAR_THRESHOLD_M and (best is None or dm < best[0]):
                    best = (dm, r["id"])
            if best:
                loc["nearRegionId"] = best[1]
                print(f"  {loc['label']:20s} -> {regions_by_id[best[1]]['name']} ({best[0]:.0f}m)")

    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\nDONE. wrote", DATA)



if __name__ == "__main__":
    main()
