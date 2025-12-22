#!/usr/bin/env python3
import argparse
import json
import os
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional

import requests
from apscheduler.schedulers.blocking import BlockingScheduler

BETMINER_BASE_URL = "https://betminer.p.rapidapi.com/bm/v2/matches"
DEFAULT_DEEPSEEK_MODEL = "deepseek-chat"
ALLOWED_COMPETITIONS = {
    "Ekstraklasa (Poland)",
    "Premier League (England)",
    "La Liga (Spain)",
    "Eerste Divisie (Netherlands)",
    "Ligue 2 (France)",
    "Premier League (Russia)",
    "Jupiler Pro League (Belgium)",
    "Eredivisie (Netherlands)",
    "Ligue 1 (France)",
    "Super League (Switzerland)",
    "Championship (England)",
    "League One (England)",
    "League Two (England)",
    "Segunda División (Spain)",
    "Bundesliga (Austria)",
    "Premiership (Scotland)",
    "Serie A (Italy)",
    "Bundesliga (Germany)",
    "2. Bundesliga (Germany)",
    "Primeira Liga (Portugal)",
    "Serie B (Italy)",
    "Süper Lig (Turkey)",
}


@dataclass
class BotConfig:
    betminer_api_key: str
    deepseek_api_key: str
    deepseek_base_url: str
    deepseek_model: str
    min_odds: float
    max_odds: float
    min_success_probability: float
    output_path: Optional[str]


def load_config() -> BotConfig:
    betminer_api_key = os.environ.get("BETMINER_API_KEY", "").strip()
    deepseek_api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    deepseek_base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    deepseek_model = os.environ.get("DEEPSEEK_MODEL", DEFAULT_DEEPSEEK_MODEL)
    min_odds = float(os.environ.get("MIN_ODDS", "1.9"))
    max_odds = float(os.environ.get("MAX_ODDS", "2.4"))
    min_success_probability = float(os.environ.get("MIN_SUCCESS_PROBABILITY", "0.65"))
    output_path = os.environ.get("OUTPUT_PATH")

    if not betminer_api_key:
        raise ValueError("Missing BETMINER_API_KEY environment variable.")
    if not deepseek_api_key:
        raise ValueError("Missing DEEPSEEK_API_KEY environment variable.")

    return BotConfig(
        betminer_api_key=betminer_api_key,
        deepseek_api_key=deepseek_api_key,
        deepseek_base_url=deepseek_base_url.rstrip("/"),
        deepseek_model=deepseek_model,
        min_odds=min_odds,
        max_odds=max_odds,
        min_success_probability=min_success_probability,
        output_path=output_path,
    )


def fetch_matches(config: BotConfig, match_date: date) -> List[Dict[str, Any]]:
    match_date_str = match_date.isoformat()
    url = f"{BETMINER_BASE_URL}/{match_date_str}/{match_date_str}"
    headers = {
        "x-rapidapi-host": "betminer.p.rapidapi.com",
        "x-rapidapi-key": config.betminer_api_key,
    }
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def extract_odds(match: Dict[str, Any]) -> Dict[str, float]:
    odds = match.get("odds") or {}
    extracted = {}
    for key, value in odds.items():
        try:
            extracted[key] = float(value)
        except (TypeError, ValueError):
            continue
    return extracted


def build_prompt(match: Dict[str, Any], odds: Dict[str, float]) -> str:
    match_details = match.get("match_details", {})
    predictions = match.get("predictions", {})
    probability = match.get("probability", {})

    return (
        "Analizza questa partita e il pronostico fornito. "
        "Restituisci solo JSON con i campi: \"recommended_market\", "
        "\"recommended_market_key\", \"estimated_success_probability\" (0-1), "
        "\"reasoning\", \"strategy\". \n\n"
        "Seleziona la singola scommessa con la maggiore probabilità di successo "
        "considerando che l'utente opererà in exchange e potrà uscire dal mercato "
        "in profitto. Scegli solo mercati con quota tra 1.90 e 2.40 se possibile. "
        "Se non c'è una buona opzione, restituisci recommended_market come null.\n\n"
        "Nel campo \"strategy\" indica come gestire la posizione in exchange "
        "(ad esempio quando entrare/uscire e come proteggere il profitto).\n\n"
        f"Dettagli partita: {json.dumps(match_details, ensure_ascii=False)}\n"
        f"Probabilità: {json.dumps(probability, ensure_ascii=False)}\n"
        f"Pronostici: {json.dumps(predictions, ensure_ascii=False)}\n"
        f"Quote disponibili: {json.dumps(odds, ensure_ascii=False)}"
    )


def call_deepseek(config: BotConfig, prompt: str) -> Dict[str, Any]:
    url = f"{config.deepseek_base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.deepseek_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config.deepseek_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Sei un analista di scommesse sportive focalizzato su selezioni ad alta "
                    "probabilità di successo per trading in exchange."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    data = response.json()
    content = data["choices"][0]["message"]["content"]
    return json.loads(content)


def is_candidate(recommendation: Dict[str, Any], odds: Dict[str, float], config: BotConfig) -> bool:
    if not recommendation:
        return False
    market_key = recommendation.get("recommended_market_key")
    if market_key is None:
        return False
    try:
        probability = float(recommendation.get("estimated_success_probability", 0))
    except (TypeError, ValueError):
        return False
    market_odds = odds.get(market_key)
    if market_odds is None:
        return False
    return (
        config.min_odds <= market_odds <= config.max_odds
        and probability >= config.min_success_probability
    )


def analyze_matches(config: BotConfig, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    results = []
    for match in matches:
        match_details = match.get("match_details", {})
        competition = match_details.get("competition_full")
        if competition not in ALLOWED_COMPETITIONS:
            continue
        odds = extract_odds(match)
        prompt = build_prompt(match, odds)
        recommendation = call_deepseek(config, prompt)
        if not recommendation or recommendation.get("recommended_market") in (None, "null"):
            continue
        if not is_candidate(recommendation, odds, config):
            continue
        results.append(
            {
                "match": match_details,
                "odds": odds,
                "recommendation": recommendation,
            }
        )
    return results


def save_results(results: List[Dict[str, Any]], output_path: Optional[str]) -> None:
    payload = json.dumps(results, ensure_ascii=False, indent=2)
    if output_path:
        with open(output_path, "w", encoding="utf-8") as handle:
            handle.write(payload)
    else:
        print(payload)


def run_once(config: BotConfig, match_date: date) -> None:
    matches = fetch_matches(config, match_date)
    results = analyze_matches(config, matches)
    save_results(results, config.output_path)


def schedule_daily(config: BotConfig, hour: int, minute: int) -> None:
    scheduler = BlockingScheduler()
    scheduler.add_job(lambda: run_once(config, date.today()), "cron", hour=hour, minute=minute)
    scheduler.start()


def main() -> None:
    parser = argparse.ArgumentParser(description="Bot per analisi pronostici con DeepSeek.")
    parser.add_argument("--run-once", action="store_true", help="Esegui subito una sola volta.")
    parser.add_argument("--date", help="Data delle partite in formato YYYY-MM-DD (default oggi).")
    parser.add_argument("--hour", type=int, default=10, help="Ora della chiamata giornaliera.")
    parser.add_argument("--minute", type=int, default=0, help="Minuto della chiamata giornaliera.")
    args = parser.parse_args()

    config = load_config()

    if args.run_once:
        match_date = date.fromisoformat(args.date) if args.date else date.today()
        run_once(config, match_date)
    else:
        schedule_daily(config, args.hour, args.minute)


if __name__ == "__main__":
    main()
