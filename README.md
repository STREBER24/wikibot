# DerIchBot

Dieses Repository beinhaltet den Code zum Betrieb des Wikipedia-Bots [DerIchBot](https://de.wikipedia.org/wiki/Benutzer:DerIchBot).

## Setup
Installiere Pakete mit `pip install -r ./requirements.txt` und ergänze die Konfigurationsdateien `telegramconfig.py` und `user-password.py` und ergänze mit `crontab -e` folgende Cronjobs:

`
0 3 * * * python3.12 /home/wikibot/main.py >> /home/wikibot/logs/main.txt
`
