import telegramconfig
import traceback
import requests
import logging
import re

def send(message: str, silent: bool=False):
    maxLogLength = 50
    logmessage = message.replace('\n', ' ↵ ')
    logging.info(f'Send telegram message: {logmessage[:maxLogLength]}{'...' if len(logmessage)>maxLogLength else ''}')
    url = f'https://api.telegram.org/bot'+telegramconfig.accessToken+'/sendMessage'
    result = requests.post(url, {'chat_id': telegramconfig.targetUser, 'text': message, 'disable_notification': silent})
    if not result.ok: logging.error(f'sending telegram message failed with status {result.status_code}')
    return result.ok


def handleException():
    logging.error(traceback.format_exc())
    send('Mimimi, du hast Müll gebaut, deshalb stürze ich jetzt ab:\n\n' + traceback.format_exc())
    

def difflink(change: dict):
    return f'https://de.wikipedia.org/wiki/Spezial:Diff/{change['revision']['new']}'


def alarmOnChange(change: dict):
    def notify(msg: str):
        logging.warning(change)
        send(f'{msg}:\n{difflink(change)}')
    if re.match('Bot: Benachrichtigung über Löschdiskussion zum Artikel', change['comment']):
        notify('XqBot aktiv')
        return True
    if change['user'] == 'TaxonBot' and re.match('^Bot: [1-9][0-9]? Abschnitte? nach \\[\\[Benutzer(in)? Diskussion:.*\\]\\] archiviert – letzte Bearbeitung: \\[\\[user:DerIchBot|DerIchBot\\]\\] \\(.*\\)$', change['comment']):
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