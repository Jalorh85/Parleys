import httpx
import json

BASE = "https://www.thesportsdb.com/api/v1/json/123"

LEAGUES = {
    "NBA": "4387",
    "MLB": "4424",
    "WNBA": "4516",
    "KBO": "4830",
}

print("=== [1] lookupleague.php - buscando campos de imagen ===\n")
league_badges = {}

with httpx.Client(timeout=10.0) as client:
    for name, league_id in LEAGUES.items():
        resp = client.get(f"{BASE}/lookupleague.php", params={"id": league_id})
        data = resp.json()
        leagues = data.get("leagues") or []
        if not leagues:
            print(f"{name}: sin respuesta")
            continue
        lg = leagues[0]
        img_fields = {k: v for k, v in lg.items() if v and any(
            kw in k.lower() for kw in ["badge", "logo", "banner", "fanart", "thumb"]
        )}
        print(f"{name} (id={league_id}): {img_fields}")
        badge = lg.get("strBadge") or lg.get("strLogo") or ""
        league_badges[name] = badge

print("\n=== [2] Alternativa: search_all_seasons.php?badge=1 ===\n")
with httpx.Client(timeout=10.0) as client:
    for name, league_id in LEAGUES.items():
        resp = client.get(f"{BASE}/search_all_seasons.php", params={"badge": "1", "id": league_id})
        data = resp.json()
        seasons = data.get("seasons") or []
        if seasons:
            print(f"{name}: primer season = {json.dumps(seasons[0])[:300]}")
        else:
            print(f"{name}: sin seasons")

print("\n=== RESUMEN: badges encontrados vía lookupleague.php ===")
for name, badge in league_badges.items():
    print(f"{name}: {badge or '(vacío)'}")
