# Trading-BOT-v1

Bot giornaliero che scarica le partite dalla tua API Betminer, analizza ogni partita una alla volta con ChatGPT (con ricerca web) e restituisce solo scommesse singole con quota tra 1,90 e 2,40 e probabilità di successo alta.

## Requisiti

- Python 3.10+
- Chiavi API:
  - `BETMINER_API_KEY`
  - `OPENAI_API_KEY`

## Installazione

```bash
pip install -r requirements.txt
```

## Configurazione

Imposta le variabili d'ambiente (esempio):

```bash
export BETMINER_API_KEY="..."
export OPENAI_API_KEY="..."
export OPENAI_BASE_URL="https://api.openai.com/v1"
export OPENAI_MODEL="gpt-5"
export MIN_ODDS="1.9"
export MAX_ODDS="2.4"
export MIN_SUCCESS_PROBABILITY="0.65"
export OUTPUT_PATH="output.json"
```

Puoi salvare queste variabili in un file `.env` nella root del progetto:

```bash
BETMINER_API_KEY="..."
OPENAI_API_KEY="..."
OPENAI_BASE_URL="https://api.openai.com/v1"
OPENAI_MODEL="gpt-5"
MIN_ODDS="1.9"
MAX_ODDS="2.4"
MIN_SUCCESS_PROBABILITY="0.65"
OUTPUT_PATH="output.json"
```

## Note API Betminer (RapidAPI)

L'API Betminer richiede **obbligatoriamente** gli header RapidAPI:

```
x-rapidapi-host: betminer.p.rapidapi.com
x-rapidapi-key: LA_TUA_API_KEY
```

Il bot li invia automaticamente usando `BETMINER_API_KEY`.

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

La scansione giornaliera considera **solo le partite della stessa giornata**. Se non ci sono partite disponibili,
il bot stampa un messaggio e produce comunque un output JSON vuoto.

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

## Avvio automatico (systemd)

Per avviare **sempre** bot e dashboard dopo il reboot, usa i servizi systemd inclusi.

1. Copia i file di servizio:

```bash
sudo cp services/trading-bot.service /etc/systemd/system/
sudo cp services/trading-dashboard.service /etc/systemd/system/
```

2. Ricarica systemd e abilita i servizi:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now trading-bot.service
sudo systemctl enable --now trading-dashboard.service
```

3. Controlla lo stato:

```bash
systemctl status trading-bot.service
systemctl status trading-dashboard.service
```

Assicurati che i percorsi in `services/*.service` corrispondano alla tua VPS
(es. `/home/ubuntu/Trading-BOT-v1` e al virtualenv).

## Avvio automatico con script unico

In alternativa puoi usare lo script `run_all.sh` per avviare dashboard e bot insieme:

```bash
./run_all.sh
```

## Output

Il bot restituisce un JSON con:

- dettagli partita
- quote disponibili
- raccomandazione di ChatGPT con strategia di exchange

Vengono inclusi solo i risultati con quota tra `MIN_ODDS` e `MAX_ODDS` e probabilità stimata >= `MIN_SUCCESS_PROBABILITY`.

## Ricerca web

ChatGPT utilizza la ricerca web integrata tramite l'API Responses di OpenAI. Non è necessario configurare
endpoint esterni: la ricerca viene gestita dal modello durante la chiamata.

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
