import wikitextparser as wtp
from typing import Literal
import recentChanges
import pywikibot
import logging
import utils
import re

def extractFromDeletionDisk(content: str):
    parsed = wtp.parse(content)
    result = ''
    for sec in parsed.sections:
        if sec.level == 1 and (sec.title or '').strip() == 'Benutzerseiten': break
        if sec.title != None:
            result += sec.level*'=' + ' ' + sec.title + ' ' + sec.level*'='
        result += sec.contents
    result = result.strip()
    if re.match('^{{Löschkandidatenseite|erl=.*}}$', result.split('\n')[0]):
        result = '\n'.join(result.split('\n')[1:])
    result = result.strip()
    if re.match('^<!-- Hinweis an den letzten Bearbeiter: Wenn alles erledigt ist, hinter "erl=" mit --~~~~ signieren. -->', result.split('\n')[0]):
        result = '\n'.join(result.split('\n')[1:])
    return result.strip()

def handleKatDiscussionUpdate(site: pywikibot._BaseSite, titel: str):
    date = titel.split('/')[2] + '-' + str(recentChanges.parseMonthDict[titel.split('/')[3]]).rjust(2,'0') + '-' + titel.split('/')[4].rjust(2,'0')
    if date < '2024-04-18': return
    logs: dict[str, str|Literal[False]] = utils.loadJson(f'data/katDiskInfo/{date}.json', {})
    diskPage = pywikibot.Page(site, titel)
    parsedDisk = parseKatDisk(diskPage)
    for kattitle, userlinks in parsedDisk.items():
        if logs.get(kattitle) != None: continue
        logs[kattitle] = False
        logging.info(f'Check category {kattitle} on category disk ...')
        creator = getPageCreator(pywikibot.Page(site, kattitle))
        if creator is None: logging.info(f'no creator of {kattitle} found'); continue
        if re.match(ipRegex, creator): logging.info(f'do not notify {creator} because he is ip'); continue
        if creator in userlinks: logging.info(f'do not notify {creator} because already on kat-disk'); continue
        userdisk = pywikibot.Page(site, f'Benutzer Diskussion:{creator}')
        renderedInfo = infoTemplate(creator, kattitle, titel)
        userdisk.text += renderedInfo
        if utils.savePage(userdisk, f'Informiere über Diskussion zu [[:{kattitle}]].'):
            logs[kattitle] = creator
            logging.info(f'Notify {creator} about kat-disk of {kattitle}')
        else:
            logging.info(f'do not notify {creator} because saving failed')
    utils.dumpJson(f'data/katDiskInfo/{date}.json', logs)

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
            userlinks = set([':'.join(link.target.split(':')[1:]) for link in sec.wikilinks if re.match('^(Benutzer:|Benutzer Diskussion:)', link.target)]+
                            [utils.findTemplateArg(template, '1') for template in sec.templates if template.name.strip().lower() == 'ping'])
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

def infoTemplate(username: str, kattitle: str, diskTitle: str):
    isIP = bool(re.match(ipRegex, username))
    return f"""
== [[:{kattitle}]] ==

Hallo{'' if isIP else ' '+username},

zu der im Betreff genannten und von dir erstellten Kategorie wurde auf [[{diskTitle}]] eine Diskussion begonnen. Du bist herzlich eingeladen, dich an der Diskussion zu beteiligen.

Ich bin übrigens nur ein [[WP:Bots|Bot]]. Wenn ich nicht richtig funktioniere, sag bitte [[Benutzer Diskussion:DerIch27|DerIch27]] bescheid. Wenn du nicht mehr von mir benachrichtigt werden möchtest, kannst du deine Benutzerdiskussionsseite auf [[Benutzer:DerIchBot/Opt-Out Liste|dieser Liste]] eintragen.

Freundliche Grüsse  --~~~~"""

if __name__ == '__main__':
    site = pywikibot.Site('de', 'wikipedia')
    print(handleKatDiscussionUpdate(site, 'Wikipedia:WikiProjekt Kategorien/Diskussionen/2024/April/18'))