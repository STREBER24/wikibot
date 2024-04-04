import recentChanges
import traceback
import utils
import flask

app = flask.Flask(__name__)

HOST = '212.132.114.61'
PORT = 80

@app.route('/aktualisiere-wartungsliste-cache')
def aktualisiere_wartungsliste_cache(): 
    if utils.checkLastUpdate('aktualisiere-wartungsliste-cache', 15):
        recentChanges.updateWikilist()
        return 'Wartungsliste erfolgreich aktualisiert. Du wirst gleich weitergeleitet ...', {"Refresh": "4; url=https://de.wikipedia.org/wiki/Benutzer:DerIchBot/Wartungsliste"}
    else:
        return 'Aktualisierung verweigert, da letzte Aktualisierung aus Cache weniger als 15 Minuten her ist.'

@app.route('/aktualisiere-wartungsliste-check')
def aktualisiere_wartungsliste_check(): 
    if utils.checkLastUpdate('aktualisiere-wartungsliste-check', 15):
        recentChanges.checkPagesInProblemList()
        recentChanges.updateWikilist()
        return 'Wartungsliste erfolgreich geprüft und aktualisiert. Du wirst gleich weitergeleitet ...', {"Refresh": "4; url=https://de.wikipedia.org/wiki/Benutzer:DerIchBot/Wartungsliste"}
    else:
        return 'Aktualisierung verweigert, da letzte Aktualisierung mit Prüfung weniger als 15 Minuten her ist.'

@app.route('/number-of-problems')
def number_of_problems():
    return f'{len(recentChanges.loadAllProblems())} Probleme im Cache'

@app.errorhandler(500)
def exception_handler(error):
    app.logger.error(f'STATUS 500\n\n{traceback.format_exc()}')
    utils.sendTelegram(f'{traceback.format_exc()}')
    return "Unerwarteter interner Fehler aufgetreten. Der Betreiber wurde bereits benachrichtigt.", 500

if __name__=='__main__': 
    app.run(host=HOST, port=PORT)
