# DerIchBot

Dieses Repository beinhaltet den Code zum Betrieb des Wikipedia-Bots [DerIchBot](https://de.wikipedia.org/wiki/Benutzer:DerIchBot).

## Setup
Installiere Pakete mit `pip install -r ./requirements.txt` und ergänze die Konfigurationsdateien `telegramconfig.py` und `user-password.py` und ergänze mit `crontab -e` folgende Cronjobs:

```
0 2 * * * cd /home/wikibot && .venv/bin/python main.py >> logs/main.log 2>>&1
*/15 * * * * cd /home/wikibot && .venv/bin/python monitoring.py 2>> logs/monitoring_err.log
```

Ergänze außerdem folgende Datei als `/etc/systemd/system/my_project.service` und starte den Service mit `systemctl start flaskserver`:
```
[Unit]
Description=Flask server
After=network.target

[Service]
WorkingDirectory=/home/wikibot
ExecStart=/home/wikibot/.venv/bin/python /home/wikibot/webserver.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Die Software ist für Python 3.12 und Ubuntu 20.04 getestet.
