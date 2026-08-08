"""
Diagnóstico rápido: pega esto en la raíz de tu proyecto y corré
    python debug_kbo.py
para ver EXACTAMENTE qué responde api-sports.io, sin pasar por tu
pipeline (que se está tragando los errores en logs que no ves).
"""
import os
import httpx
import json

API_SPORTS_KEY = os.environ.get("API_SPORTS_KEY", "721b2f330a081784fcd13aa87d87063b")
API_SPORTS_BASE = "https://v1.baseball.api-sports.io"

print(f"Key en uso: {API_SPORTS_KEY[:8]}...{API_SPORTS_KEY[-4:]}")
print("=" * 60)

with httpx.Client(timeout=10.0) as client:
    # 1. Buscar la liga KBO
    print("\n[1] Buscando liga KBO...")
    resp = client.get(
        f"{API_SPORTS_BASE}/leagues",
        headers={"x-apisports-key": API_SPORTS_KEY},
        params={"search": "KBO"},
    )
    print(f"Status HTTP: {resp.status_code}")
    data = resp.json()
    print(f"errors: {data.get('errors')}")
    print(f"results: {data.get('results')}")
    if data.get("response"):
        for r in data["response"]:
            lg = r.get("league", {})
            print(f"  -> id={lg.get('id')} name={lg.get('name')}")
            for season in r.get("seasons", []):
                print(f"     season disponible: {season.get('season')} (coverage: {season.get('coverage', {}).get('games')})")
    else:
        print("  (sin resultados en 'response')")

    print("\nJSON crudo completo (primeros 2000 chars):")
    print(json.dumps(data, indent=2)[:2000])
