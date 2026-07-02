# Best Weather Route 🌤️🚐

En liten agent som rangerer campingsteder langs Norge/Sverige/Danmark-kysten
basert på hvor været er best de neste N dagene — høyest temperatur, mest sol,
minst vind.

Bruker [Open-Meteo](https://open-meteo.com/) (gratis, ingen API-nøkkel) og kan
kjøres manuelt, via cron, eller automatisk hver dag med GitHub Actions.

## Hvordan det virker

1. Henter daglig værvarsel for en liste med kandidatsteder (`CANDIDATES` i
   `best_weather_route.py`)
2. Normaliserer temperatur, soltimer og vind på tvers av stedene
3. Regner ut en vektet score per sted (standard: 40 % temp, 35 % sol, 25 % vind)
4. Rangerer stedene og skriver ut resultatet
5. (Valgfritt) Sender push-varsel via [ntfy.sh](https://ntfy.sh) hvis beste
   sted har endret seg siden forrige kjøring

## Kjør lokalt

```bash
pip install requests
python3 best_weather_route.py --days 3
```

Med varsel:

```bash
python3 best_weather_route.py --days 3 --notify --ntfy-topic mitt-eget-navn
```

Abonner på samme topic-navn i ntfy-appen (iOS/Android) for å få varsel på
telefonen.

## Kjør automatisk med GitHub Actions

Se `.github/workflows/daily-weather-check.yml` — kjører hver morgen kl. 07
norsk tid, helt gratis, uten at du trenger egen server.

## Tilpasning

- **Legg til/fjern steder:** rediger `CANDIDATES`-listen
- **Endre vekting:** rediger `WEIGHTS`-dict (må summere til 1.0)
- **Endre tidshorisont:** `--days` (opptil 16 dager, men nøyaktigheten synker
  fort etter dag 5-7)

## Lisens

Fritt til eget bruk.
