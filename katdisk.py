import wikitextparser as wtp
from typing import Literal
import recentChanges
import pywikibot
import logging
import utils
import time
import re

def extractFromDeletionDisk(content: str) -> tuple[str,str]: # (Kategorien, Rest)
    parsed = wtp.parse(content)
    result = ''
    ok = False
    for sec in parsed.sections:
        if sec.level == 1 and (sec.title or '').strip() == 'Benutzerseiten': ok = True; break
        if sec.title != None:
            result += '\n' + sec.level*'=' + ' ' + sec.title + ' ' + sec.level*'=' + '\n\n' + sec.contents
            del sec.title
            sec.contents = ''
        else:
            split = sec.contents.strip().split('\n')
            newContents = []
            if len(split)>0 and re.match('^{{Löschkandidatenseite|erl=.*}}$', split[0]):
                newContents.append(split[0])
                split.pop(0)
            while len(split)>0 and split[0].strip() == '':
                split.pop(0)
            if len(split)>0 and re.match('^<!-- Hinweis an den letzten Bearbeiter: Wenn alles erledigt ist, hinter "erl=" mit --~~~~ signieren. -->', split[0]):
                newContents.append(split[0])
                split.pop(0)
            sec.contents = '\n'.join(newContents) + '\n\n'
            result += '\n'.join(split)
    if not ok:
        raise Exception(f'Keine Überschrift Benutzerdiskussionsseiten auf Löschkandidatenseite gefunden.')
    return result.strip().strip().replace('\n<span></span>\n','\n').replace('\n\n\n', '\n\n'), parsed.string.strip().replace('\n\n\n', '\n\n')

NOTIFICATION_DELAY = 60*15 # 15min
def handleKatDiscussionUpdate(site: pywikibot._BaseSite, titel: str):
    date = titel.split('/')[2] + '-' + str(recentChanges.parseMonthDict[titel.split('/')[3]]).rjust(2,'0') + '-' + titel.split('/')[4].rjust(2,'0')
    if date < '2024-04-18': return
    logs: dict[str, int|str|Literal[False]] = utils.loadJson(f'data/katDiskInfo/{date}.json', {})
    diskPage = pywikibot.Page(site, titel)
    parsedDisk = parseKatDisk(diskPage)
    outstandingNotifications: tuple[dict[str,list[str]], dict[str,list[str]]] = ({}, {}) # (suspended notifications, necessary notifications)
    for kattitle, userlinks in parsedDisk.items():
        logstate = logs.get(kattitle)
        if logstate == None: 
            logs[kattitle] = int(time.time())
        elif isinstance(logstate, int) and logstate+NOTIFICATION_DELAY < time.time():
            logs[kattitle] = False
        else:
            continue
        logging.info(f'Check category {kattitle} on category disk ...')
        creator = getPageCreator(pywikibot.Page(site, kattitle))
        if creator is None: logging.info(f'no creator of {kattitle} found'); continue
        if re.match(ipRegex, creator): logging.info(f'do not notify {creator} because he is ip'); continue
        if creator in userlinks: logging.info(f'do not notify {creator} because already on kat-disk'); continue
        if utils.isBlockedForInfinity(site, creator): logging.info(f'do not notify {creator} because he is blocked'); continue 
        if outstandingNotifications[int(logs[kattitle]==False)].get(creator) == None: outstandingNotifications[int(logs[kattitle]==False)][creator] = []
        outstandingNotifications[int(logs[kattitle]==False)][creator].append(kattitle)
    for creator in outstandingNotifications[1]:
        kattitles = outstandingNotifications[1][creator] + (outstandingNotifications[0].get(creator) or [])
        if notify(site, creator, kattitles, titel):
            for kat in kattitles:
                logs[kat] = creator
    utils.dumpJson(f'data/katDiskInfo/{date}.json', logs)


def handleKatDiscussionToday():
    site = pywikibot.Site('de', 'wikipedia')
    date = time.localtime()
    diskTitle = f'Wikipedia:WikiProjekt Kategorien/Diskussionen/{date.tm_year}/{['Januar','Februar','März','April','Mai','Juni','Juli','August','September','Oktober','November','Dezember'][date.tm_mon-1]}/{date.tm_mday}'
    handleKatDiscussionUpdate(site, diskTitle)


def notify(site, creator: str, kattitles: list[str], diskTitle: str):
    userdisk = pywikibot.Page(site, f'Benutzer Diskussion:{creator}')
    renderedInfo = infoTemplate(creator, kattitles, diskTitle)
    userdisk.text += renderedInfo
    if utils.savePage(userdisk, f'Informiere über Diskussion zu {' und '.join([f'[[:{i}]]' for i in kattitles])}.', botflag=False):
        logging.info(f'Notify {creator} about kat-disk of {' and '.join(kattitles)}')
        return True
    logging.info(f'do not notify {creator} because saving failed')
    return False


def parseKatDisk(page: pywikibot.Page):
    result: dict[str,set[str]] = {} # {pagetitle: userlinks}
    content = page.text
    parsed = wtp.parse(content)
    for sec in parsed.sections:
        if sec.level != 2: continue
        titellinks = wtp.parse(sec.title).wikilinks
        for link in titellinks:
            if not link.target.startswith(':Kategorie:'): continue
            kattitle = link.target[1:]
            userlinks = utils.extractUserLinks(sec)
            result[kattitle] = userlinks
    return result

def getPageCreator(page: pywikibot.Page) -> str|None:
    try:
        for rev in page.revisions(reverse=True, total=1):
            return rev['user']
        return None
    except pywikibot.exceptions.NoPageError:
        return None

ipRegex = re.compile('^(((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])|((([0-9a-fA-F]){1,4})\\:){7}([0-9a-fA-F]){1,4})$') 

def infoTemplate(username: str, kattitles: list[str], diskTitle: str):
    isIP = bool(re.match(ipRegex, username))
    assert len(kattitles) > 0
    return f"""
== [[:{kattitles[0]}]]{' und '+str(len(kattitles)-1)+' weitere' if len(kattitles)>1 else ''} ==

Hallo{'' if isIP else ' '+username},

zu {len(kattitles) if len(kattitles)>1 else 'der im Betreff genannten und'} von dir erstellten Kategorie{'n' if len(kattitles)>1 else ''} wurde auf [[{diskTitle}]] eine Diskussion begonnen. Du bist herzlich eingeladen, dich an der Diskussion zu beteiligen.

Ich bin übrigens nur ein [[WP:Bots|Bot]]. Wenn ich nicht richtig funktioniere, sag bitte [[Benutzer Diskussion:DerIch27|DerIch27]] bescheid. Wenn du nicht mehr von mir benachrichtigt werden möchtest, kannst du deine Benutzerdiskussionsseite auf [[Benutzer:DerIchBot/Opt-Out Liste|dieser Liste]] eintragen.

Freundliche Grüsse  --~~~~"""

if __name__ == '__main__':
    site = pywikibot.Site('de', 'wikipedia')
    print(handleKatDiscussionUpdate(site, 'Wikipedia:WikiProjekt Kategorien/Diskussionen/2024/April/18'))