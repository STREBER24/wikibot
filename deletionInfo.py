import wikitextparser as wtp
import recentChanges
import pywikibot
import requests
import optOut
import utils
import re

def handleDeletionDiscussionUpdate(site: pywikibot._BaseSite, titel: str):
    date = recentChanges.parseWeirdDateFormats(titel[26:])
    if date < '2024-04-06': return
    logs: dict[str, list[str]] = utils.loadJson(f'data/deletionInfo/{date}.json', {})
    parsedDeletionDisk = parseDeletionDisk(pywikibot.Page(site, titel))
    for pagetitle, userlinks in parsedDeletionDisk.items():
        if logs.get(pagetitle) != None: continue
        logs[pagetitle] = []
        mainAuthors = getMainAuthors(pywikibot.Page(site, pagetitle))
        for author in mainAuthors:
            if author in userlinks: continue
            userdisk = pywikibot.Page(site, f'Benutzer Diskussion:{author}')
            if checkForExistingInfoOnDisk(userdisk, pagetitle): continue
            renderedInfo = infoTemplate(author, pagetitle, titel)
            if addToPage(userdisk, renderedInfo, f'Informiere über Löschantrag zu [[{pagetitle}]].'):
                logs[pagetitle].append(author)
                print(f'Notify {author} about deletion disk of {pagetitle}')
        utils.dumpJson(f'data/deletionInfo/{date}.json', logs)

def parseDeletionDisk(page: pywikibot.Page):
    result: dict[str,set[str]] = {} # {pagetitle: userlinks}
    content = page.get()
    parsed = wtp.parse(content)
    for sec in parsed.sections:
        if sec.level != 2: continue
        titellinks = wtp.parse(sec.title).wikilinks
        if len(titellinks) == 0: continue
        pagetitle = titellinks[0].target
        userlinks = set([':'.join(link.target.split(':')[1:]) for link in sec.wikilinks if re.match('^(Benutzer:|Benutzer Diskussion:)', link.target)])
        result[pagetitle] = userlinks
    return result

def checkUserExistance(username: str) -> bool:
    res: dict = requests.get(f'https://www.mediawiki.org/w/api.php?action=query&meta=globaluserinfo&format=json&guiuser={username}').json()
    return (res.get('query') != None) and (res.get('error') == None)

def getMainAuthors(page: pywikibot.Page) -> set[str]:
    try:
        relevantAuthors: set[str] = set()
        authors: dict[str,int|float] = {}
        for rev in page.revisions():
            if authors.get(rev['user']) == None:
                authors[rev['user']] = 0
                if not checkUserExistance(rev['user']): 
                    continue # kommt vor, wenn Artikel aus anderem wiki importiert wurde
            if rev['parentid'] == 0:
                relevantAuthors.add(rev['user'])
            authors[rev['user']] += 0.21 if rev['minor'] else 1
        for autor in authors:
            if authors[autor] >= max(authors.values()):
                relevantAuthors.add(autor)
            if authors[autor] >= sum(authors.values())/3:
                relevantAuthors.add(autor)
        return relevantAuthors
    except pywikibot.exceptions.NoPageError:
        return set()
    
def checkForExistingInfoOnDisk(disk: pywikibot.Page, pagetitle: str):
    try:
        content = disk.get()
        parsed = wtp.parse(content)
        for sec in parsed.sections:
            if sec.title is None: continue
            if pagetitle not in sec.title: continue
            if 'lösch' in sec.contents.lower(): return True
        return False
    except pywikibot.exceptions.NoPageError:
        return False

ipRegex = re.compile('^(((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])|((([0-9a-fA-F]){1,4})\\:){7}([0-9a-fA-F]){1,4})$')   

def infoTemplate(username: str, pagetitle: str, deletionDiskTitle: str):
    isIP = bool(re.match(ipRegex, username))
    return f"""
== [[{pagetitle}]] ==

Hallo{'' if isIP else ' '+username},

gegen den im Betreff genannten, von dir angelegten oder erheblich ausgebauten Artikel wurde ein Löschantrag gestellt (nicht von mir). Bitte entnimm den Grund dafür der '''[[{deletionDiskTitle}|Löschdiskussion]]'''. Ob der Artikel tatsächlich gelöscht wird, wird sich gemäß unserer [[WP:Löschregeln|Löschregeln]] im Laufe der siebentägigen Löschdiskussion entscheiden. 

Du bist herzlich eingeladen, dich an der [[{deletionDiskTitle}|Löschdiskussion]] zu beteiligen. Wenn du möchtest, dass der Artikel behalten wird, kannst du dort die Argumente, die für eine Löschung sprechen, entkräften, indem du dich beispielsweise zur [[Wikipedia:Relevanzkriterien|enzyklopädischen Relevanz]] des Artikels äußerst. Du kannst auch während der Löschdiskussion Artikelverbesserungen vornehmen, die die Relevanz besser erkennen lassen und die [[Wikipedia:Artikel#Mindestanforderungen|Mindestqualität]] sichern.

Da bei Wikipedia jeder Löschanträge stellen darf, sind manche Löschanträge auch offensichtlich unbegründet; solche Anträge kannst du ignorieren.

Vielleicht fühlst du dich durch den Löschantrag vor den Kopf gestoßen, weil durch den Antrag die Arbeit, die Du in den Artikel gesteckt hast, nicht gewürdigt wird. [[WP:Sei tapfer|Sei tapfer]] und [[Wikipedia:Wikiquette|bleibe dennoch freundlich]]. Der andere meint es [[WP:Geh von guten Absichten aus|vermutlich auch gut]].

Ich bin übrigens nur ein [[WP:Bots|Bot]]. Wenn ich nicht richtig funktioniere, sag bitte [[Benutzer Diskussion:DerIch27|DerIch27]] bescheid. Wenn du nicht mehr von mir benachrichtigt werden möchtest, kannst du dich auf [[Benutzer:DerIchBot/Opt-Out Liste|dieser Liste]] eintragen.

Freundliche Grüsse  --~~~~"""

def addToPage(page: pywikibot.Page, text: str, summary: str):
    if optOut.includes(page.title()):
        return False
    page.text = page.text + text
    page.save(botflag=True, summary=f'Bot: {summary}')
    return True

if __name__ == '__main__':
    site = pywikibot.Site('de', 'wikipedia')
    site.login()
    handleDeletionDiscussionUpdate(site, 'Wikipedia:Löschkandidaten/6. April 2024')
