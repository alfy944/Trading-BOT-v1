# Trading-BOT-v1

Bot giornaliero che scarica le partite dalla tua API Betminer, analizza ogni partita una alla volta con DeepSeek e restituisce solo scommesse singole con quota tra 1,90 e 2,40 e probabilità di successo alta.

## Requisiti

- Python 3.10+
- Chiavi API:
  - `BETMINER_API_KEY`
  - `DEEPSEEK_API_KEY`

## Installazione

```bash
pip install -r requirements.txt
```

## Configurazione

Imposta le variabili d'ambiente (esempio):

```bash
export BETMINER_API_KEY="..."
export DEEPSEEK_API_KEY="..."
export DEEPSEEK_BASE_URL="https://api.deepseek.com/v1"
export DEEPSEEK_MODEL="deepseek-chat"
export MIN_ODDS="1.9"
export MAX_ODDS="2.4"
export MIN_SUCCESS_PROBABILITY="0.65"
export OUTPUT_PATH="output.json"
```

## Uso

### Esecuzione immediata (una sola volta)

```bash
python trading_bot.py --run-once --date 2024-11-06
```

### Esecuzione giornaliera alle 10:00

```bash
python trading_bot.py
```

Puoi cambiare orario con:

```bash
python trading_bot.py --hour 10 --minute 0
```

## Dashboard

La dashboard mostra i risultati del file JSON generato dal bot.

Assicurati di impostare `OUTPUT_PATH` (o `DASHBOARD_DATA_PATH`) con il file dei risultati:

```bash
export OUTPUT_PATH="output.json"
python trading_bot.py --run-once --date 2024-11-06
```

Avvia la dashboard:

```bash
python dashboard.py
```

Apri `http://localhost:5000` nel browser.

## Output

Il bot restituisce un JSON con:

- dettagli partita
- quote disponibili
- raccomandazione di DeepSeek con strategia di exchange

Vengono inclusi solo i risultati con quota tra `MIN_ODDS` e `MAX_ODDS` e probabilità stimata >= `MIN_SUCCESS_PROBABILITY`.

## Campionati supportati

Vengono considerate solo le seguenti competizioni:

- Ekstraklasa (Poland)
- Premier League (England)
- La Liga (Spain)
- Eerste Divisie (Netherlands)
- Ligue 2 (France)
- Premier League (Russia)
- Jupiler Pro League (Belgium)
- Eredivisie (Netherlands)
- Ligue 1 (France)
- Super League (Switzerland)
- Championship (England)
- League One (England)
- League Two (England)
- Segunda División (Spain)
- Bundesliga (Austria)
- Premiership (Scotland)
- Serie A (Italy)
- Bundesliga (Germany)
- 2. Bundesliga (Germany)
- Primeira Liga (Portugal)
- Serie B (Italy)
- Süper Lig (Turkey)
