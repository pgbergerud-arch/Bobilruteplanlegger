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
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ---------------------------------------------------------------------------
# 1) KANDIDATSTEDER — faktiske campingplasser med 4.0+ i Google-vurdering
#    Norge, Sverige og Danmark. Legg til/fjern så mange du vil.
# ---------------------------------------------------------------------------
CANDIDATES = [
    # --- NORGE: Oslofjorden / Sørlandet ---
    {"name": "Langøya Camping (Oslo)", "lat": 59.8722, "lon": 10.7154},
    {"name": "Aktivitetsbyen Gamle Fredrikstad", "lat": 59.2009, "lon": 10.9629},
    {"name": "Enhus Camping (Fredrikstad)", "lat": 59.1860, "lon": 10.9021},
    {"name": "Fredrikstad Bobilparking", "lat": 59.2226, "lon": 10.9173},
    {"name": "Arendal", "lat": 58.4611, "lon": 8.7692},
    {"name": "Kristiansand Feriesenter", "lat": 58.1220, "lon": 8.0658},
    {"name": "Solplassen & Rakke Camping (Stavern)", "lat": 58.9842, "lon": 10.0303},
    {"name": "Larvik Bobilparkering", "lat": 59.0490, "lon": 10.0335},
    {"name": "Granholmen Camping (Sandefjord)", "lat": 59.0888, "lon": 10.2229},
    {"name": "Asnes Camping (Sandefjord)", "lat": 59.0983, "lon": 10.2419},
    {"name": "Vora Camping (Sandefjord)", "lat": 59.0715, "lon": 10.2596},
    {"name": "Langeby Camping (Sandefjord)", "lat": 59.0789, "lon": 10.2627},
    {"name": "Ørastranda Camping (Nøtterøy)", "lat": 59.2143, "lon": 10.3702},
    {"name": "Nøtterøy Familiecamping Fjærholmen", "lat": 59.2250, "lon": 10.4633},
    {"name": "Furustrand AS (Tolvsrød)", "lat": 59.2731, "lon": 10.4916},
    # --- NORGE: Vestlandet ---
    {"name": "Stavanger", "lat": 58.9700, "lon": 5.7331},
    {"name": "Mosvangen Camping (Stavanger)", "lat": 58.9524, "lon": 5.7140},
    {"name": "Haraldshaugen Camping (Haugesund)", "lat": 59.4277, "lon": 5.2585},
    {"name": "Lone Camping (Bergen)", "lat": 60.3735, "lon": 5.4592},
    {"name": "Bratland Camping (Bergen)", "lat": 60.3523, "lon": 5.4353},
    {"name": "Skjerva bobilparkering (Ålesund)", "lat": 62.4692, "lon": 6.1327},
    {"name": "Voss Camping", "lat": 60.6246, "lon": 6.4214},
    {"name": "Lothepus camping og hytter (Odda)", "lat": 60.0649, "lon": 6.5529},
    {"name": "Forde Guesthouse & Camping", "lat": 61.4496, "lon": 5.8922},
    {"name": "Førde Bobilparkering", "lat": 61.4581, "lon": 5.8464},
    {"name": "Krokane Camping AS (Florø)", "lat": 61.5935, "lon": 5.0712},
    # --- NORGE: Innlandet (Mjøsa-regionen, Østerdalen, Valdres) ---
    {"name": "Olympiaparken sommercamping (Lillehammer)", "lat": 61.1329, "lon": 10.5060},
    {"name": "Lillehammer Turistsenter", "lat": 61.1260, "lon": 10.4417},
    {"name": "Wohnmobil-Parkplatz Strandvegen (Hamar)", "lat": 60.8020, "lon": 11.0264},
    {"name": "Topcamp Mjøsa (Brumunddal)", "lat": 60.8795, "lon": 10.8907},
    {"name": "Gjøvik Campingsenter", "lat": 60.8195, "lon": 10.6776},
    {"name": "Sveastranda Camping (Gjøvik)", "lat": 60.8890, "lon": 10.6757},
    {"name": "Gjøvik bobilpark Furuseth Gård", "lat": 60.8161, "lon": 10.6787},
    {"name": "Elverum Camping", "lat": 60.8668, "lon": 11.5562},
    {"name": "Sigernessjøen Family Camping", "lat": 60.1182, "lon": 12.0538},
    {"name": "Rena camping leisure", "lat": 61.1384, "lon": 11.3796},
    {"name": "Fagernes Camping Park", "lat": 60.9818, "lon": 9.2314},
    {"name": "Fossen Camping Fagernes", "lat": 61.0333, "lon": 9.1769},
    {"name": "First Camp Beitostølen (Valdres)", "lat": 61.2413, "lon": 8.9200},
    {"name": "Bøflaten Camping (Vang i Valdres)", "lat": 61.1306, "lon": 8.5445},
    {"name": "Rogn Camping (Ryfoss, Valdres)", "lat": 61.1519, "lon": 8.7259},
    # --- NORGE: Setesdal ---
    {"name": "Odden Camping (Evje)", "lat": 58.5857, "lon": 7.7943},
    {"name": "Oddestemmen Steinsliperi og Camping (Evje)", "lat": 58.6008, "lon": 7.8430},
    {"name": "Fennefoss Camping (Evje/Hornnes)", "lat": 58.5752, "lon": 7.7763},
    {"name": "Hovden Fjellstoge (Setesdal)", "lat": 59.5794, "lon": 7.3891},
    {"name": "Byklestøylane Camping (Bykle)", "lat": 59.3894, "lon": 7.3929},
    # --- NORGE: Telemark ---
    {"name": "Notodden Bobilcamp", "lat": 59.5584, "lon": 9.2492},
    {"name": "Lystang Camping (Notodden)", "lat": 59.4621, "lon": 9.3191},
    {"name": "Sandviken Camping (Austbygde/Rjukan)", "lat": 59.9890, "lon": 8.8167},
    {"name": "Tinnsjø Kro Camping (Rjukan)", "lat": 59.9255, "lon": 8.8010},
    {"name": "Rjukan Hytteby", "lat": 59.8787, "lon": 8.6058},
    {"name": "Bø Camping", "lat": 59.4445, "lon": 9.0630},
    {"name": "Beverøya Hytteutleie og Camping (Bø)", "lat": 59.4105, "lon": 9.0899},
    {"name": "Åsgrav Family Camping (Bø)", "lat": 59.4107, "lon": 9.1098},
    {"name": "Sanda Camping og Hytteutleie (Bø)", "lat": 59.4201, "lon": 8.9048},
    {"name": "Kragerøfjorden Camping", "lat": 58.8434, "lon": 9.3533},
    {"name": "Jomfruland Camping (Kragerø)", "lat": 58.8572, "lon": 9.5775},
    {"name": "Seljord Camping", "lat": 59.4858, "lon": 8.6518},
    {"name": "Seljord Ferieland", "lat": 59.4816, "lon": 8.6409},
    {"name": "Sanden Camping (Seljord)", "lat": 59.4555, "lon": 8.7297},
    # --- NORGE: Sogn og Fjordane ---
    {"name": "Kjørnes Camping (Sogndal)", "lat": 61.2117, "lon": 7.1210},
    {"name": "Uteplassen Sogndal Fjell og natur-camping", "lat": 61.3391, "lon": 6.9264},
    {"name": "Laerdal Holiday and Leisure Park", "lat": 61.1005, "lon": 7.4697},
    {"name": "Veganeset Camping (Balestrand)", "lat": 61.2158, "lon": 6.5620},
    # --- NORGE: Trøndelag / Nord-Norge ---
    {"name": "Storsand Gård Camping (Trondheim)", "lat": 63.4322, "lon": 10.7086},
    {"name": "Lofoten Beach Camp", "lat": 68.1032, "lon": 13.2946},
    {"name": "Rystad Lofoten Camping", "lat": 68.2778, "lon": 14.3035},
    {"name": "Moskenes Camping (Lofoten)", "lat": 67.9001, "lon": 13.0524},
    {"name": "Lofoten Bobilcamping", "lat": 68.2253, "lon": 14.2172},
    {"name": "Lofoten Fjordcamp", "lat": 68.2040, "lon": 13.8875},
    {"name": "Tromso Camping", "lat": 69.6475, "lon": 19.0140},
    # --- SVERIGE ---
    {"name": "Brädäng Camping (Stockholm)", "lat": 59.2956, "lon": 17.9232},
    {"name": "Gålö Havsbad (Stockholm skärgård)", "lat": 59.0951, "lon": 18.3184},
    {"name": "Askrike Camping (Vaxholm)", "lat": 59.3868, "lon": 18.2441},
    {"name": "Göteborg", "lat": 57.7089, "lon": 11.9746},
    {"name": "Halmstad", "lat": 56.6745, "lon": 12.8567},
    {"name": "Destination Apelviken (Varberg)", "lat": 57.0880, "lon": 12.2479},
    {"name": "Getteröns Camping (Varberg)", "lat": 57.1165, "lon": 12.2141},
    {"name": "Espeviks Camping (Varberg)", "lat": 57.1911, "lon": 12.1897},
    {"name": "Kalmar Camping Rafshagsudden", "lat": 56.7570, "lon": 16.3798},
    {"name": "Vita Sands Camping (Kalmar)", "lat": 56.5686, "lon": 16.2251},
    {"name": "Böda Sand (Öland)", "lat": 57.2741, "lon": 17.0513},
    {"name": "Sandbybadets Camping (Öland)", "lat": 57.1739, "lon": 17.0374},
    {"name": "Sandviks Camping (Öland)", "lat": 56.3790, "lon": 16.4036},
    {"name": "KronoCamping Saxnäs (Öland)", "lat": 56.6863, "lon": 16.4836},
    {"name": "Kneippbyn Camping (Gotland)", "lat": 57.6097, "lon": 18.2428},
    {"name": "Solhaga Camping (Fårö)", "lat": 57.8899, "lon": 19.0910},
    {"name": "Fide Äventyrsby & Camping (Gotland)", "lat": 57.0920, "lon": 18.3010},
    # --- SVERIGE: Bohuslän / Halland (vestkysten) ---
    {"name": "First Camp City Strömstad", "lat": 58.9305, "lon": 11.1799},
    {"name": "Lagunen Camping & Stugor (Strömstad)", "lat": 58.9135, "lon": 11.2052},
    {"name": "Daftö Resort (Strömstad)", "lat": 58.9040, "lon": 11.1999},
    {"name": "Selätter Camping (Strömstad)", "lat": 58.9565, "lon": 11.1573},
    {"name": "Hafsten Resort & Camping (Uddevalla)", "lat": 58.3145, "lon": 11.7235},
    {"name": "Fossen Camping (Uddevalla)", "lat": 58.3173, "lon": 11.5650},
    {"name": "Hansagårds Camping (Falkenberg)", "lat": 56.8744, "lon": 12.5298},
    {"name": "Olofsbo Camping (Falkenberg)", "lat": 56.9229, "lon": 12.3924},
    {"name": "Hansagård Camping Strand (Falkenberg)", "lat": 56.8721, "lon": 12.5270},
    {"name": "Åsa Camping & Havsbad", "lat": 57.3483, "lon": 12.1223},
    {"name": "Rörviks camping (Onsala)", "lat": 57.4175, "lon": 11.9402},
    {"name": "Camp Gressela", "lat": 57.4545, "lon": 12.1341},
    {"name": "Vallersvik Camping and Hostel", "lat": 57.3207, "lon": 12.1589},
    # --- SVERIGE: Midt-Sverige (Småland, Vänern/Vättern/Mälaren) ---
    {"name": "Öjaby Camping (Växjö)", "lat": 56.9011, "lon": 14.7396},
    {"name": "Evedals Camping (Växjö)", "lat": 56.9228, "lon": 14.8178},
    {"name": "Lovsjöbadens Camping (Jönköping)", "lat": 57.6626, "lon": 14.1837},
    {"name": "Habo Camping & Stugby (Vättern)", "lat": 57.8782, "lon": 14.1104},
    {"name": "Måräng Camping (Finspång)", "lat": 58.5854, "lon": 15.8759},
    {"name": "Söderköpings Camping", "lat": 58.4770, "lon": 16.3345},
    {"name": "Skeppsdockans Vandrarhem (Söderköping)", "lat": 58.4920, "lon": 16.3052},
    {"name": "Dalbergså Camping (Vänern)", "lat": 58.5968, "lon": 12.5928},
    {"name": "Sörbostrands Camping (Vänern)", "lat": 58.4937, "lon": 12.4442},
    {"name": "Askevik Camping (Vänern)", "lat": 58.8889, "lon": 14.0135},
    {"name": "Duse Udde Camping (Vänern)", "lat": 59.0820, "lon": 12.8850},
    {"name": "Vätterviksbadet (Vadstena, Vättern)", "lat": 58.4656, "lon": 14.9333},
    {"name": "First Camp Gränna (Vättern)", "lat": 58.0277, "lon": 14.4582},
    {"name": "Harge Bad & Camping (Vättern)", "lat": 58.7838, "lon": 14.9737},
    {"name": "Sjöbacka camping (Vättern)", "lat": 58.0435, "lon": 14.1879},
    {"name": "First Camp Västerås (Mälaren)", "lat": 59.5745, "lon": 16.5199},
    {"name": "Mälarbadens camping (Mälaren)", "lat": 59.4517, "lon": 16.4366},
    {"name": "Mariefreds Camping (Mälaren)", "lat": 59.2632, "lon": 17.2556},
    # --- SVERIGE: Sør (Skåne) ---
    {"name": "Ystad Camping (Fritidsvägen)", "lat": 55.4326, "lon": 13.8624},
    {"name": "Campervan parking (Ystad)", "lat": 55.4249, "lon": 13.7864},
    {"name": "Charlottesborgs Camping (Kristianstad)", "lat": 56.0196, "lon": 14.1268},
    {"name": "Martin's Smokehouse and Camping (Yngsjö)", "lat": 55.8608, "lon": 14.2204},
    # --- DANMARK ---
    {"name": "København", "lat": 55.6761, "lon": 12.5683},
    {"name": "Skagen", "lat": 57.7208, "lon": 10.5844},
    {"name": "DCU-Camping Aarhus Blommehaven", "lat": 56.1103, "lon": 10.2323},
    {"name": "First Camp Ajstrup Strand (Aarhus)", "lat": 56.0415, "lon": 10.2643},
    {"name": "Saksild Strand Camping (Odder)", "lat": 55.9797, "lon": 10.2479},
    {"name": "DCU-Camping Odense", "lat": 55.3696, "lon": 10.3928},
    {"name": "Esbjerg Camping A/S", "lat": 55.5128, "lon": 8.3886},
    {"name": "Sannes Familiecamping (Bornholm)", "lat": 55.1959, "lon": 14.9865},
    {"name": "Møllers Dueodde Camping (Bornholm)", "lat": 54.9958, "lon": 15.0789},
    {"name": "Gudhjem Camping (Bornholm)", "lat": 55.2077, "lon": 14.9771},
    {"name": "Lyngholt Familiecamping (Bornholm)", "lat": 55.2555, "lon": 14.7623},
    {"name": "Bornholms Familie-Camping", "lat": 55.0051, "lon": 15.0951},
]

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Vekting av de tre faktorene (må summere til 1.0)
WEIGHTS = {
    "temperature": 0.40,
    "sunshine": 0.35,
    "wind": 0.25,  # lavere vind = bedre, håndteres i scoring
}

DAILY_VARS = [
    "temperature_2m_max",
    "sunshine_duration",
    "windspeed_10m_max",
    "precipitation_probability_max",
]

# Antall steder per API-kall. Open-Meteo støtter batching via kommaseparerte
# koordinater i én forespørsel, noe som er langt mer stabilt og raskere enn
# ett kall per sted (unngår rate limiting / tilfeldige timeouts). Mindre
# batcher er raskere å behandle server-side og gir kortere respons-ventetid.
BATCH_SIZE = 15

# Gjenbrukbar session med automatiske retries ved timeout/serverfeil.
# Open-Meteo sin gratis-API har ingen oppetids-garanti og deler IP-rom med
# mange andre tjenester (Vercel, GitHub Actions osv.) — sporadiske timeouts
# er et kjent, dokumentert problem på deres side, ikke noe galt med koden.
_session = requests.Session()
_retry = Retry(
    total=3,
    backoff_factor=2,  # 2s, 4s, 8s mellom forsøk
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
)
_session.mount("https://", HTTPAdapter(max_retries=_retry))

REQUEST_TIMEOUT = 45  # sekunder per forsøk


# ---------------------------------------------------------------------------
# 2) HENT VÆRDATA (batchet, med retries)
# ---------------------------------------------------------------------------
class BatchFetchError(Exception):
    """Kastes når en batch ikke lot seg hente selv etter retries."""


def fetch_forecast_batch(places: list[dict], days: int) -> list[dict]:
    """Henter daglig værvarsel for en gruppe steder i ett API-kall."""
    params = {
        "latitude": ",".join(str(p["lat"]) for p in places),
        "longitude": ",".join(str(p["lon"]) for p in places),
        "daily": ",".join(DAILY_VARS),
        "forecast_days": min(days, 16),
        "timezone": "auto",
    }
    try:
        resp = _session.get(OPEN_METEO_URL, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise BatchFetchError(f"Klarte ikke hente vær for {len(places)} steder: {e}") from e
    data = resp.json()
    # Ved kun ett sted returnerer Open-Meteo et enkelt objekt, ikke en liste
    return data if isinstance(data, list) else [data]


def chunked(seq: list, size: int):
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


# ---------------------------------------------------------------------------
# 3) SCORING
# ---------------------------------------------------------------------------
def score_candidates(days: int) -> list[dict]:
    raw = []
    failed_batches = 0
    skipped_places = []

    for batch in chunked(CANDIDATES, BATCH_SIZE):
        try:
            results = fetch_forecast_batch(batch, days)
        except BatchFetchError as e:
            # Ikke la én treg/feilende batch krasje hele kjøringen —
            # hopp over disse stedene denne runden og fortsett med resten.
            failed_batches += 1
            skipped_places.extend(p["name"] for p in batch)
            print(f"ADVARSEL: {e}")
            continue

        for place, result in zip(batch, results):
            daily = result["daily"]
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

    if failed_batches:
        print(
            f"\n{failed_batches} batch(er) feilet og ble hoppet over "
            f"({len(skipped_places)} steder uten data denne runden): "
            f"{', '.join(skipped_places[:10])}"
            + (" …" if len(skipped_places) > 10 else "")
        )

    if not raw:
        raise RuntimeError(
            "Ingen steder ga værdata denne runden — Open-Meteo er sannsynligvis "
            "midlertidig nede eller treg. Avbryter uten å overskrive tidligere resultater."
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
RESULTS_FILE = os.path.join(os.path.dirname(__file__), "docs", "results.json")


def load_last_best():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f).get("name")
    return None


def save_last_best(name: str):
    with open(STATE_FILE, "w") as f:
        json.dump({"name": name, "updated": datetime.now(timezone.utc).isoformat()}, f)


def save_results_json(ranked: list[dict], days: int):
    """Skriver rangert resultat til docs/results.json for dashboardet (index.html)."""
    os.makedirs(os.path.dirname(RESULTS_FILE), exist_ok=True)
    payload = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "days": days,
        "places": [
            {
                "rank": i + 1,
                "name": r["name"],
                "lat": r["lat"],
                "lon": r["lon"],
                "score": r["score"],
                "avg_temp_c": r["avg_temp_c"],
                "avg_sun_hours": r["avg_sun_hours"],
                "avg_wind_kmh": r["avg_wind_kmh"],
                "avg_precip_prob": r["avg_precip_prob"],
            }
            for i, r in enumerate(ranked)
        ],
    }
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


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

    save_results_json(ranked, args.days)

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
    try:
        main()
    except RuntimeError as e:
        print(f"\nFEIL: {e}")
        raise SystemExit(1)
