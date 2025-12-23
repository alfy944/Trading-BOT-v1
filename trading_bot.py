#!/usr/bin/env python3
import argparse
import json
import logging
import os
from dataclasses import dataclass
from datetime import date
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, List, Optional

import requests

BETMINER_BASE_URL = "https://betminer.p.rapidapi.com/bm/v2/matches"
DEFAULT_OPENAI_MODEL = "gpt-5"
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
    openai_api_key: str
    openai_base_url: str
    openai_model: str
    log_path: str
    log_max_bytes: int
    log_backup_count: int
    min_odds: float
    max_odds: float
    min_success_probability: float
    output_path: Optional[str]


def load_config() -> BotConfig:
    betminer_api_key = os.environ.get("BETMINER_API_KEY", "").strip()
    openai_api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    openai_base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    openai_model = os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    log_path = os.environ.get("LOG_PATH", "logs/trading_bot.log")
    log_max_bytes = int(os.environ.get("LOG_MAX_BYTES", "1048576"))
    log_backup_count = int(os.environ.get("LOG_BACKUP_COUNT", "5"))
    min_odds = float(os.environ.get("MIN_ODDS", "1.9"))
    max_odds = float(os.environ.get("MAX_ODDS", "2.4"))
    min_success_probability = float(os.environ.get("MIN_SUCCESS_PROBABILITY", "0.65"))
    output_path = os.environ.get("OUTPUT_PATH")

    if not betminer_api_key:
        raise ValueError("Missing BETMINER_API_KEY environment variable.")
    if not openai_api_key:
        raise ValueError("Missing OPENAI_API_KEY environment variable.")

    return BotConfig(
        betminer_api_key=betminer_api_key,
        openai_api_key=openai_api_key,
        openai_base_url=openai_base_url.rstrip("/"),
        openai_model=openai_model,
        log_path=log_path,
        log_max_bytes=log_max_bytes,
        log_backup_count=log_backup_count,
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
    logging.info("Fetching matches for %s", match_date_str)
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


def call_chatgpt(config: BotConfig, prompt: str) -> Dict[str, Any]:
    url = f"{config.openai_base_url}/responses"
    headers = {
        "Authorization": f"Bearer {config.openai_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config.openai_model,
        "input": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Sei un analista di scommesse sportive focalizzato su selezioni ad alta "
                            "probabilità di successo per trading in exchange."
                        ),
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                ],
            },
        ],
        "tools": [{"type": "web_search_preview"}],
        "temperature": 0.2,
    }
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    data = response.json()
    output_text = ""
    for item in data.get("output", []):
        if item.get("type") == "message":
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    output_text += content.get("text", "")
    return json.loads(output_text)


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


def analyze_matches(
    config: BotConfig,
    matches: List[Dict[str, Any]],
    target_date: date,
) -> List[Dict[str, Any]]:
    results = []
    skipped_competition = 0
    skipped_date = 0
    for match in matches:
        match_details = match.get("match_details", {})
        match_date_str = match_details.get("match_date")
        if match_date_str:
            match_day = match_date_str.split(" ")[0]
            if match_day != target_date.isoformat():
                skipped_date += 1
                continue
        competition = match_details.get("competition_full")
        if competition not in ALLOWED_COMPETITIONS:
            skipped_competition += 1
            continue
        odds = extract_odds(match)
        prompt = build_prompt(match, odds)
        recommendation = call_chatgpt(config, prompt)
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
    logging.info(
        "Analysis done: %d results, %d skipped by date, %d skipped by competition",
        len(results),
        skipped_date,
        skipped_competition,
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
    results = analyze_matches(config, matches, match_date)
    if not results:
        logging.info("Nessuna partita trovata per la giornata odierna.")
    save_results(results, config.output_path)


def setup_logging(config: BotConfig) -> None:
    log_dir = os.path.dirname(config.log_path)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    handler = RotatingFileHandler(
        config.log_path,
        maxBytes=config.log_max_bytes,
        backupCount=config.log_backup_count,
        encoding="utf-8",
    )
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    logging.basicConfig(level=logging.INFO, handlers=[handler])


def main() -> None:
    parser = argparse.ArgumentParser(description="Bot per analisi pronostici con ChatGPT.")
    parser.add_argument("--date", help="Data delle partite in formato YYYY-MM-DD (default oggi).")
    args = parser.parse_args()

    config = load_config()
    setup_logging(config)

    match_date = date.fromisoformat(args.date) if args.date else date.today()
    run_once(config, match_date)


if __name__ == "__main__":
    main()
