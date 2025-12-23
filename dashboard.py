#!/usr/bin/env python3
import json
import os
from datetime import datetime
from typing import Any, Dict, List

from flask import Flask, render_template_string

app = Flask(__name__)

TEMPLATE = """
<!doctype html>
<html lang="it">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Dashboard Pronostici</title>
    <style>
      body { font-family: Arial, sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; }
      header { padding: 24px 32px; background: #111827; border-bottom: 1px solid #1f2937; }
      h1 { margin: 0 0 8px; font-size: 24px; }
      .meta { color: #94a3b8; font-size: 14px; }
      main { padding: 24px 32px; }
      .card { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 16px; margin-bottom: 16px; }
      .card h2 { margin: 0 0 8px; font-size: 18px; }
      .row { display: flex; flex-wrap: wrap; gap: 16px; }
      .pill { padding: 4px 10px; border-radius: 999px; background: #0ea5e9; color: #0f172a; font-weight: 700; font-size: 12px; }
      table { width: 100%; border-collapse: collapse; margin-top: 12px; }
      th, td { text-align: left; padding: 8px; border-bottom: 1px solid #334155; font-size: 14px; }
      th { color: #cbd5f5; }
      .empty { color: #94a3b8; padding: 24px; border: 1px dashed #334155; border-radius: 12px; }
    </style>
  </head>
  <body>
    <header>
      <h1>Dashboard pronostici</h1>
      <div class="meta">Aggiornato: {{ updated_at }} · File: {{ data_path }}</div>
    </header>
    <main>
      {% if results %}
        {% for item in results %}
          <div class="card">
            <div class="row">
              <h2>{{ item.match.home_team }} vs {{ item.match.away_team }}</h2>
              <span class="pill">{{ item.match.competition_full }}</span>
            </div>
            <div class="meta">{{ item.match.match_date }}</div>
            <table>
              <tr>
                <th>Mercato consigliato</th>
                <td>{{ item.recommendation.recommended_market }}</td>
              </tr>
              <tr>
                <th>Quota</th>
                <td>{{ item.recommended_odds }}</td>
              </tr>
              <tr>
                <th>Probabilità stimata</th>
                <td>{{ item.recommendation.estimated_success_probability }}</td>
              </tr>
              <tr>
                <th>Strategia exchange</th>
                <td>{{ item.recommendation.strategy }}</td>
              </tr>
              <tr>
                <th>Motivazione</th>
                <td>{{ item.recommendation.reasoning }}</td>
              </tr>
            </table>
          </div>
        {% endfor %}
      {% else %}
        <div class="empty">Nessun pronostico disponibile. Assicurati di avere generato il file JSON.</div>
      {% endif %}
    </main>
  </body>
</html>
"""


def load_results(data_path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(data_path):
        return []
    with open(data_path, "r", encoding="utf-8") as handle:
        content = handle.read().strip()
        if not content:
            return []
        payload = json.loads(content)
        if not isinstance(payload, list):
            return []
        return payload


def enrich_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    enriched = []
    for item in results:
        odds = item.get("odds", {})
        recommendation = item.get("recommendation", {})
        market_key = recommendation.get("recommended_market_key")
        recommended_odds = odds.get(market_key)
        enriched.append({
            "match": item.get("match", {}),
            "odds": odds,
            "recommendation": recommendation,
            "recommended_odds": recommended_odds,
        })
    return enriched


@app.route("/")
def index() -> str:
    data_path = os.environ.get("DASHBOARD_DATA_PATH") or os.environ.get("OUTPUT_PATH") or "output.json"
    results = enrich_results(load_results(data_path))
    updated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    return render_template_string(
        TEMPLATE,
        results=results,
        updated_at=updated_at,
        data_path=data_path,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
