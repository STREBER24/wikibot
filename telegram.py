import telegramconfig
import traceback
import requests
import logging
import re

def send(message: str, silent: bool=False):
    maxLogLength = 40
    logging.info(f'Sent telegram message: {message[:maxLogLength]}{'...' if len(message)>maxLogLength else ''}')
    url = f'https://api.telegram.org/bot'+telegramconfig.accessToken+'/sendMessage'
    return requests.post(url, {'chat_id': telegramconfig.targetUser, 'text': message, 'disable_notification': silent}).ok


def handleException():
    logging.error(traceback.format_exc())
    send('Mimimi, du hast mich nicht gut programmiert, deshalb stürze ich jetzt ab:\n\n' + traceback.format_exc())
    

def alarmOnChange(change: dict):
    def notify(msg: str):
        logging.warning(change)
        send(f'{msg}:\nhttps://de.wikipedia.org/wiki/Spezial:Diff/{change['revision']['new']}')
    if re.match('Bot: Benachrichtigung über Löschdiskussion zum Artikel', change['comment']):
        notify('XqBot aktiv')
        return True
    if change['user'] == 'TaxonBot' and re.match('^Bot: [1-9][0-9]? Abschnitte? nach \\[\\[Benutzer Diskussion:.*\\]\\] archiviert – letzte Bearbeitung: \\[\\[user:DerIchBot|DerIchBot\\]\\] \\(.*\\)$', change['comment']):
        return False
    if change['user'] == 'DerIchBot':
        return False
    if 'DerIchBot' in change['comment']:
        notify('DerIchBot erwähnt')
        return True
    watchlist = ['Vorlage:Platinpreis', 'Vorlage:Goldpreis', 'Vorlage:Speedcubing-Rekorddatum', 'Vorlage:Speedcubing-Rekordevent', 
                 'Vorlage:Speedcubing-Rekordhalter', 'Vorlage:Speedcubing-Rekordzeit']
    if change['title'] in watchlist:
        notify('Beobachtete Seite bearbeitet.')
        return True