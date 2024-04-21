# DerIchBot

Dieses Repository beinhaltet den Code zum Betrieb des Wikipedia-Bots [DerIchBot](https://de.wikipedia.org/wiki/Benutzer:DerIchBot).

## Setup
Installiere Pakete mit `pip install -r ./requirements.txt` und ergänze die Konfigurationsdateien `telegramconfig.py` und `user-password.py` und ergänze mit `crontab -e` folgende Cronjobs:

```
0 2 * * * cd /home/wikibot && .venv/bin/python main.py >> logs/main.log 2>>&1
*/15 * * * * cd /home/wikibot && .venv/bin/python monitoring.py 2>> logs/monitoring_err.log
```

Ergänze außerdem Dateien der Form `/etc/systemd/system/<...>.service` für `webserver.py` und `recentChanges.py` und registriere die Services mit `systemctl enable <...>`:
```
[Unit]
Description=<...>
After=network.target

[Service]
WorkingDirectory=/home/wikibot
ExecStart=/home/wikibot/.venv/bin/python /home/wikibot/<...>.py
Restart=on-abnormal
StandardOutput=append:/home/wikibot/logs/<...>.log
StandardError=append:/home/wikibot/logs/<...>_err.log

[Install]
WantedBy=multi-user.target
```

Die Software ist für Python 3.12 und Ubuntu 20.04 getestet.
