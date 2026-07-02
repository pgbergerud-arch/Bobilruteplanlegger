#!/usr/bin/env python3
"""
best_weather_route.py

Agent som kontinuerlig vurderer hvilket campingsted som har best vær
(høyest temperatur, mest sol, minst vind) de neste N dager.

Bruk:
    python3 best_weather_route.py
    python3 best_weather_route.py --days 3 --notify

Krever:
    pip install requests
"""

import argparse
import json
import os
from datetime import datetime, timezone

import requests

# ---------------------------------------------------------------------------
# 1) KANDIDATSTEDER — legg til/fjern så mange du vil
# ---------------------------------------------------------------------------
CANDIDATES = [
    {"name": "Arendal", "lat": 58.4611, "lon": 8.7692},
    {"name": "Kristiansand", "lat": 58.1467, "lon": 7.9956},
    {"name": "Stavern/Larvik", "lat": 58.9842, "lon": 10.0303},
    {"name": "Sandefjord", "lat": 59.0889, "lon": 10.2229},
    {"name": "Nøtterøy/Tønsberg", "lat": 59.2143, "lon": 10.3702},
    {"name": "Stavanger", "lat": 58.9700, "lon": 5.7331},
    {"name": "Göteborg", "lat": 57.7089, "lon": 11.9746},
    {"name": "Halmstad", "lat": 56.6745, "lon": 12.8567},
    {"name": "København", "lat": 55.6761, "lon": 12.5683},
    {"name": "Skagen", "lat": 57.7208, "lon": 10.5844},
]

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Vekting av de tre faktorene (må summere til 1.0)
WEIGHTS = {
    "temperature": 0.40,
    "sunshine": 0.35,
    "wind": 0.25,  # lavere vind = bedre, håndteres i scoring
}


# ---------------------------------------------------------------------------
# 2) HENT VÆRDATA
# ---------------------------------------------------------------------------
def fetch_forecast(lat: float, lon: float, days: int) -> dict:
    """Henter daglig værvarsel fra Open-Meteo for gitt koordinat."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": ",".join(
            [
                "temperature_2m_max",
                "sunshine_duration",
                "windspeed_10m_max",
                "precipitation_probability_max",
            ]
        ),
        "forecast_days": min(days, 16),
        "timezone": "auto",
    }
    resp = requests.get(OPEN_METEO_URL, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()["daily"]


# ---------------------------------------------------------------------------
# 3) SCORING
# ---------------------------------------------------------------------------
def score_candidates(days: int) -> list[dict]:
    raw = []
    for place in CANDIDATES:
        daily = fetch_forecast(place["lat"], place["lon"], days)
        n = len(daily["time"])
        avg_temp = sum(daily["temperature_2m_max"][:n]) / n
        avg_sun_hours = sum(daily["sunshine_duration"][:n]) / n / 3600  # sek -> timer
        avg_wind = sum(daily["windspeed_10m_max"][:n]) / n
        avg_precip_prob = sum(daily["precipitation_probability_max"][:n]) / n

        raw.append(
            {
                "name": place["name"],
                "lat": place["lat"],
                "lon": place["lon"],
                "avg_temp_c": round(avg_temp, 1),
                "avg_sun_hours": round(avg_sun_hours, 1),
                "avg_wind_kmh": round(avg_wind, 1),
                "avg_precip_prob": round(avg_precip_prob, 0),
                "daily": daily,
            }
        )

    # Normaliser hver faktor 0-1 på tvers av kandidatene, så vi kan vekte dem
    temps = [r["avg_temp_c"] for r in raw]
    suns = [r["avg_sun_hours"] for r in raw]
    winds = [r["avg_wind_kmh"] for r in raw]

    def norm(val, lo, hi, invert=False):
        if hi == lo:
            return 0.5
        n = (val - lo) / (hi - lo)
        return 1 - n if invert else n

    for r in raw:
        t_score = norm(r["avg_temp_c"], min(temps), max(temps))
        s_score = norm(r["avg_sun_hours"], min(suns), max(suns))
        w_score = norm(r["avg_wind_kmh"], min(winds), max(winds), invert=True)  # lavere vind = bedre

        r["score"] = round(
            WEIGHTS["temperature"] * t_score
            + WEIGHTS["sunshine"] * s_score
            + WEIGHTS["wind"] * w_score,
            3,
        )

    raw.sort(key=lambda r: r["score"], reverse=True)
    return raw


# ---------------------------------------------------------------------------
# 4) VARSLING (valgfritt) — gratis push via ntfy.sh, ingen konto nødvendig
# ---------------------------------------------------------------------------
def notify_ntfy(topic: str, message: str, title: str = "Værrute-agent"):
    try:
        requests.post(
            f"https://ntfy.sh/{topic}",
            data=message.encode("utf-8"),
            headers={"Title": title},
            timeout=10,
        )
    except Exception as e:
        print(f"Kunne ikke sende varsel: {e}")


# ---------------------------------------------------------------------------
# 5) TILSTAND — husk forrige beste sted, så vi kun varsler ved endring
# ---------------------------------------------------------------------------
STATE_FILE = os.path.join(os.path.dirname(__file__), "last_best.json")


def load_last_best():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f).get("name")
    return None


def save_last_best(name: str):
    with open(STATE_FILE, "w") as f:
        json.dump({"name": name, "updated": datetime.now(timezone.utc).isoformat()}, f)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Finn beste værrute for camping")
    parser.add_argument("--days", type=int, default=3, help="Antall dager frem (default 3)")
    parser.add_argument("--notify", action="store_true", help="Send push-varsel via ntfy.sh")
    parser.add_argument("--ntfy-topic", default="mitt-varrute-varsel", help="ntfy.sh topic-navn")
    args = parser.parse_args()

    ranked = score_candidates(args.days)

    print(f"\nBeste steder de neste {args.days} dagene ({datetime.now():%Y-%m-%d %H:%M}):\n")
    print(f"{'#':<3}{'Sted':<20}{'Score':<8}{'Temp°C':<9}{'Sol(t)':<9}{'Vind km/h':<11}{'Nedbør%'}")
    for i, r in enumerate(ranked, 1):
        print(
            f"{i:<3}{r['name']:<20}{r['score']:<8}{r['avg_temp_c']:<9}"
            f"{r['avg_sun_hours']:<9}{r['avg_wind_kmh']:<11}{r['avg_precip_prob']}"
        )

    best = ranked[0]
    last_best = load_last_best()

    if args.notify and best["name"] != last_best:
        msg = (
            f"Nytt beste sted: {best['name']}\n"
            f"Temp: {best['avg_temp_c']}°C, Sol: {best['avg_sun_hours']}t, "
            f"Vind: {best['avg_wind_kmh']} km/h, Nedbør: {best['avg_precip_prob']}%"
        )
        notify_ntfy(args.ntfy_topic, msg)
        print(f"\n>> Varsel sendt (endring fra '{last_best}' til '{best['name']}')")

    save_last_best(best["name"])


if __name__ == "__main__":
    main()
