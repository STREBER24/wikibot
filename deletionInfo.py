import wikitextparser as wtp
import recentChanges
import pywikibot
import optOut
import utils
import re

def handleDeletionDiscussionUpdate(site: pywikibot._BaseSite, titel: str):
    date = recentChanges.parseWeirdDateFormats(titel[26:])
    if date is None or  date < '2024-04-06': return
    logs: dict[str, dict[str,dict]] = utils.loadJson(f'data/deletionInfo/{date}.json', {})
    parsedDeletionDisk = parseDeletionDisk(pywikibot.Page(site, titel))
    for pagetitle, userlinks in parsedDeletionDisk.items():
        if logs.get(pagetitle) != None: continue
        print(f'Check page {pagetitle} on deletion disk ...')
        allTitles, mainAuthors = parseRevisionHistory(pywikibot.Page(site, pagetitle))
        if any([logs.get(i)!=None for i in allTitles]): continue
        for author in mainAuthors:
            if not mainAuthors[author]['major']: continue
            if re.match(ipRegex, author): print(f'do not notify {author} because he is ip'); continue
            if author in userlinks: print(f'do not notify {author} because already on deletion disk'); continue
            if author in utils.loadJson('data/opt-out-ld.json', []): print(f'do not notify {author} because of opt out'); continue
            userdisk = pywikibot.Page(site, f'Benutzer Diskussion:{author}')
            if checkForExistingInfoOnDisk(userdisk, pagetitle): continue
            renderedInfo = infoTemplate(author, pagetitle, titel)
            if addToPage(userdisk, renderedInfo, f'Informiere über Löschantrag zu [[{pagetitle}]].'):
                mainAuthors[author]['notified'] = True
                print(f'Notify {author} about deletion disk of {pagetitle}')
            else:
                print(f'do not notify {author} because saving failed')
        logs[pagetitle] = sortMainAuthors(mainAuthors)[-5:]
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

def sortMainAuthors(authors: dict[str,dict]):
    return sorted(authors.items(), key=lambda autor: autor[1]['score']+1e10*autor[1]['creator'])

def parseRevisionHistory(page: pywikibot.Page) -> tuple[set[str], dict[str,dict]]:
    print(f'parse revision history of page {page.title()} ...')
    try:
        allTitles: set[str] = {page.title()}
        authors: dict[str,dict] = {}
        pagesize = 0
        for rev in page.revisions(reverse=True):
            if re.match('.*verschob die Seite \\[\\[(.)*\\]\\] nach \\[\\[(.)*\\]\\].*', rev['comment']):
                for link in wtp.parse(rev['comment']).wikilinks:
                    allTitles.add(link.target)
            if authors.get(rev['user']) == None:
                if re.match(interwikiRegex, rev['user']): continue
                authors[rev['user']] = {'score': 0, 'major': False, 'notified': False, 'creator': False}
            if rev['parentid'] == 0:
                authors[rev['user']]['major'] = True
                authors[rev['user']]['creator'] = True
            sizediff = max(0, rev['size']-pagesize); pagesize = rev['size']
            authors[rev['user']]['score'] += (sizediff**0.5)/10
            authors[rev['user']]['score'] += 1/3 if rev['minor'] else 1
        for autor in authors:
            if authors[autor]['score'] < 3: continue
            if authors[autor]['score'] >= max([author['score'] for author in authors.values()]):
                authors[autor]['major'] = True
            if authors[autor]['score'] >= sum([author['score'] for author in authors.values()])/3:
                authors[autor]['major'] = True
        return allTitles, authors
    except pywikibot.exceptions.NoPageError:
        print('pgae not found :-(')
        return set(), dict()
    
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
interwikiRegex = re.compile('^en>')  

def infoTemplate(username: str, pagetitle: str, deletionDiskTitle: str):
    isIP = bool(re.match(ipRegex, username))
    return f"""
== [[{pagetitle}]] ==

Hallo{'' if isIP else ' '+username},

gegen den im Betreff genannten, von dir angelegten oder erheblich bearbeiteten Artikel wurde ein Löschantrag gestellt (nicht von mir). Bitte entnimm den Grund dafür der '''[[{deletionDiskTitle}#{pagetitle.replace(' ','_')}|Löschdiskussion]]'''. Ob der Artikel tatsächlich gelöscht wird, wird sich gemäß unserer [[WP:Löschregeln|Löschregeln]] im Laufe der siebentägigen Löschdiskussion entscheiden. 

Du bist herzlich eingeladen, dich an der [[{deletionDiskTitle}#{pagetitle.replace(' ','_')}|Löschdiskussion]] zu beteiligen. Wenn du möchtest, dass der Artikel behalten wird, kannst du dort die Argumente, die für eine Löschung sprechen, entkräften, indem du dich beispielsweise zur [[Wikipedia:Relevanzkriterien|enzyklopädischen Relevanz]] des Artikels äußerst. Du kannst auch während der Löschdiskussion Artikelverbesserungen vornehmen, die die Relevanz besser erkennen lassen und die [[Wikipedia:Artikel#Mindestanforderungen|Mindestqualität]] sichern.

Da bei Wikipedia jeder Löschanträge stellen darf, sind manche Löschanträge auch offensichtlich unbegründet; solche Anträge kannst du ignorieren.

Vielleicht fühlst du dich durch den Löschantrag vor den Kopf gestoßen, weil durch den Antrag die Arbeit, die Du in den Artikel gesteckt hast, nicht gewürdigt wird. [[WP:Sei tapfer|Sei tapfer]] und [[Wikipedia:Wikiquette|bleibe dennoch freundlich]]. Der andere meint es [[WP:Geh von guten Absichten aus|vermutlich auch gut]].

Ich bin übrigens nur ein [[WP:Bots|Bot]]. Wenn ich nicht richtig funktioniere, sag bitte [[Benutzer Diskussion:DerIch27|DerIch27]] bescheid. Wenn du nicht mehr von mir benachrichtigt werden möchtest, kannst du dich auf [[Benutzer:Xqbot/Opt-out:LD-Hinweis|dieser]] oder [[Benutzer:DerIchBot/Opt-Out Liste|dieser Liste]] eintragen.

Freundliche Grüsse  --~~~~"""

def addToPage(page: pywikibot.Page, text: str, summary: str):
    if optOut.includes(page.title()):
        return False
    page.text = page.text + text
    try:
        page.save(summary=f'Bot: {summary}')
        return True
    except pywikibot.exceptions.LockedPageError:
        return False

if __name__ == '__main__':
    site = pywikibot.Site('de', 'wikipedia')
    site.login()
    page = pywikibot.Page(site, 'Walter Schmidt (Rechtswissenschaftler, 1934)')
    print(parseRevisionHistory(page))
    #handleDeletionDiscussionUpdate(site, 'Wikipedia:Löschkandidaten/heute')
