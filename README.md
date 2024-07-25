# DerIchBot

Dieses Repository beinhaltet den Code zum Betrieb des Wikipedia-Bots [DerIchBot](https://de.wikipedia.org/wiki/Benutzer:DerIchBot).

## Setup
Installiere Pakete mit `pip install -r ./requirements.txt` und ergänze die Konfigurationsdatei `user-password.py` sowie eine `.env` mit folgenden Umgebungsvariablen:
```
TELEGRAM_TARGET_USER = ...
TELEGRAM_ACCESS_TOKEN = ...
TELEGRAM_DISABLED = 0
DELETION_NOTIFICATION_ENABLED = 1
DATA_FOLDER = /home/wikibot/data
``` 

Ergänze weiter mit `crontab -e` folgende Cronjobs:

```
0 2 * * * cd /home/wikibot && .venv/bin/python/src cron-daily.py >> ../logs/daily.log 2>>../logs/daily.log
0 * * * * cd /home/wikibot && .venv/bin/python/src cron-hourly.py >> ../logs/hourly.log 2>>../logs/hourly.log
*/15 * * * * cd /home/wikibot && .venv/bin/python/src monitoring.py 2>> ../logs/monitoring.log
```

Ergänze außerdem Dateien der Form `/etc/systemd/system/<...>.service` für `webserver.py` und `recentChanges.py` und registriere die Services mit `systemctl enable <...>`:
```
[Unit]
Description=<...>
After=network.target

[Service]
WorkingDirectory=/home/wikibot/src
ExecStart=/home/wikibot/.venv/bin/python /home/wikibot/src/<...>.py
Restart=on-abnormal
StandardOutput=append:/home/wikibot/logs/<...>.log
StandardError=append:/home/wikibot/logs/<...>.log

[Install]
WantedBy=multi-user.target
```

Die Software ist für Python 3.12 und Ubuntu 20.04 getestet.
