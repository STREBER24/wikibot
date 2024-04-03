# DerIchBot

Dieses Repository beinhaltet den Code zum Betrieb des Wikipedia-Bots [DerIchBot](https://de.wikipedia.org/wiki/Benutzer:DerIchBot).

## Setup
Installiere Pakete mit `pip install -r ./requirements.txt` und ergänze die Konfigurationsdateien `telegramconfig.py` und `user-password.py` und ergänze mit `crontab -e` folgende Cronjobs:

```
0 2 * * * cd /home/wikibot/ && python main.py >> logs/main.log
*/15 * * * * cd /home/wikibot/ && python monitoring.py > /dev/null 2>&1
```

Die Software ist für Python 3.12 getestet.