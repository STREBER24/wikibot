import wikitextparser as wtp
import recentChanges
import pywikibot
import logging
import katdisk
import utils
import re

def handleDeletionDiscussionUpdate(site: pywikibot._BaseSite, titel: str, change: dict|None = None):
    assert re.match('^Wikipedia:Löschkandidaten/.', titel)
    date = recentChanges.parseWeirdDateFormats(titel[26:])
    if date is None or date is False or date < '2024-04-06': return
    logs: dict[str, dict[str,dict]] = utils.loadJson(f'data/deletionInfo/{date}.json', {})
    deletionDiskPage = pywikibot.Page(site, titel) 
    wrongKats, rest = katdisk.extractFromDeletionDisk(deletionDiskPage.text)
    if wrongKats != '': 
        logging.info('Verschiebe Eintrag von Löschdiskussionsseite nach WikiProjekt Kategorien')
        logging.info(change)
        utils.sendTelegram(f'Eintrag zu Kategorien auf Löschdiskussionsseite:\n{titel}', silent=True)
        userLink = '???' if change is None else f'[[Benutzer:{change['user']}]]'
        katDiskLink = f'Wikipedia:WikiProjekt Kategorien/Diskussionen/{date[:4]}/{['Januar','Februar','März','April','Mai','Juni','Juli','August','September','Oktober','November','Dezember'][int(date[5:7])-1]}/{int(date[8:10])}'
        deletionDiskPage.text = rest
        utils.savePage(deletionDiskPage, f'Verschiebe Beitrag von {userLink} nach [[{katDiskLink}]]', botflag=True)
        katDiskPage = pywikibot.Page(site, katDiskLink)
        katDiskPage.text += '\n' + wrongKats
        utils.savePage(katDiskPage, f'Verschiebe Beitrag von {userLink} aus [[{titel}]]', botflag=True)
        return
    parsedDeletionDisk = parseDeletionDisk(deletionDiskPage)
    for pagetitle, userlinks in parsedDeletionDisk.items():
        try:
            if logs.get(pagetitle) != None: continue
            logging.info(f'Check page {pagetitle} on deletion disk ...')
            allTitles, mainAuthors = parseRevisionHistory(pywikibot.Page(site, pagetitle))
            if any([logs.get(i)!=None for i in allTitles]): continue
            for author in mainAuthors:
                if not mainAuthors[author]['major']: continue
                if re.match(ipRegex, author): logging.info(f'do not notify {author} because he is ip'); continue
                if author in userlinks: logging.info(f'do not notify {author} because already on deletion disk'); continue
                if author in utils.loadJson('data/opt-out-ld.json', []): logging.info(f'do not notify {author} because of opt out'); continue
                if utils.isBlockedForInfinity(site, author): logging.info(f'do not notify {author} because he is blocked'); continue
                userdisk = pywikibot.Page(site, f'Benutzer Diskussion:{author}')
                if checkForExistingInfoOnDisk(userdisk, allTitles): logging.info(f'do not notify {author} because already notified on userdisk');  continue
                renderedInfo = infoTemplate(author, pagetitle, titel)
                userdisk.text += renderedInfo
                if utils.savePage(userdisk, f'Informiere über Löschantrag zu [[{pagetitle}]].', botflag=False):
                    mainAuthors[author]['notified'] = True
                    logging.info(f'Notify {author} about deletion disk of {pagetitle}')
                else:
                    logging.info(f'do not notify {author} because saving failed')
            logs[pagetitle] = dict(sortMainAuthors(mainAuthors)[-5:])
            utils.dumpJson(f'data/deletionInfo/{date}.json', logs)
        except Exception as e:
            e.add_note(f'failed while checking page {pagetitle} on deletion disk')
            raise e

def parseDeletionDisk(page: pywikibot.Page):
    result: dict[str,set[str]] = {} # {pagetitle: userlinks}
    content = page.text
    parsed = wtp.parse(content)
    for sec in parsed.sections:
        if sec.level != 2: continue
        titellinks = wtp.parse(sec.title).wikilinks
        if len(titellinks) == 0: continue
        pagetitle = titellinks[0].target
        if re.search('\\((erl\\., )?(LAE|LAZ)\\)', sec.title): logging.debug(f'ignore {pagetitle} because LAE'); continue
        userlinks = set([':'.join(link.target.split(':')[1:]) for link in sec.wikilinks if re.match('^(Benutzer:|Benutzer Diskussion:)', link.target)])
        result[pagetitle] = userlinks
    return result

def sortMainAuthors(authors: dict[str,dict]):
    return sorted(authors.items(), key=lambda autor: autor[1]['score']+1e10*autor[1]['creator'])

def parseRevisionHistory(page: pywikibot.Page) -> tuple[set[str], dict[str,dict]]:
    logging.info(f'parse revision history of page {page.title()} ...')
    try:
        allTitles: set[str] = {page.title()}
        authors: dict[str,dict] = {}
        pagesize = 0
        for rev in page.revisions(reverse=True):
            if re.search('verschob die Seite \\[\\[(.)*\\]\\] nach \\[\\[(.)*\\]\\]', rev['comment']):
                for link in wtp.parse(rev['comment']).wikilinks:
                    allTitles.add(link.target)
            user = rev['user'][3:] if rev['user'].startswith('de>') else rev['user']
            if authors.get(user) == None:
                if re.match(interwikiRegex, user): continue
                authors[user] = {'score': 0, 'major': False, 'notified': False, 'creator': False}
            if rev['parentid'] == 0:
                authors[user]['major'] = True
                authors[user]['creator'] = True
            sizediff = max(0, rev['size']-pagesize); pagesize = rev['size']
            authors[user]['score'] += (sizediff**0.5)/10
            authors[user]['score'] += 1/3 if rev['minor'] else 1
        for autor in authors:
            if authors[autor]['score'] < 3: continue
            if authors[autor]['score'] >= max([author['score'] for author in authors.values()]):
                authors[autor]['major'] = True
            if authors[autor]['score'] >= sum([author['score'] for author in authors.values()])/3:
                authors[autor]['major'] = True
        return allTitles, authors
    except pywikibot.exceptions.NoPageError:
        logging.info('page not found :-(')
        return set(), dict()
    
def checkForExistingInfoOnDisk(disk: pywikibot.Page, pagetitles: set[str]):
    try:
        parsed = wtp.parse(disk.text)
        for pagetitle in pagetitles:
            for sec in parsed.sections:
                if sec.title is None: continue
                if (pagetitle not in sec.title) and (wtp.parse(pagetitle).plain_text() not in sec.title): continue
                if 'lösch' in sec.contents.lower(): return True
        return False
    except pywikibot.exceptions.InvalidTitleError:
        logging.warn(f'got invalid title while checking for existing info on disk')
        return False

ipRegex = re.compile('^(((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])|((([0-9a-fA-F]){1,4})\\:){7}([0-9a-fA-F]){1,4})$') 
interwikiRegex = re.compile('^[a-z][a-z]>')  

def infoTemplate(username: str, pagetitle: str, deletionDiskTitle: str):
    isIP = bool(re.match(ipRegex, username))
    sectiontitle = pagetitle.replace(' ','_')
    if pagetitle.startswith(':Vorlage') or pagetitle.startswith('Vorlage:'):
        return f"""
== [[{pagetitle}]] ==

Hallo{'' if isIP else ' '+username},

gegen die im Betreff genannte, von dir angelegte oder erheblich bearbeitete Vorlage wurde ein Löschantrag gestellt (nicht von mir). Bitte entnimm den Grund dafür der '''[[{deletionDiskTitle}#{sectiontitle[1:]}|Löschdiskussion]]'''. Ob die Vorlage tatsächlich gelöscht wird, wird sich gemäß unserer [[WP:Löschregeln|Löschregeln]] im Laufe der siebentägigen Löschdiskussion entscheiden. 

Du bist herzlich eingeladen, dich an der [[{deletionDiskTitle}#{pagetitle.replace(' ','_')}|Löschdiskussion]] zu beteiligen. Wenn du möchtest, dass die Vorlage behalten wird, kannst du dort die Argumente, die für eine Löschung sprechen, entkräften. Du kannst auch während der Löschdiskussion Verbesserungen an der Vorlage vornehmen.

Da bei Wikipedia jeder Löschanträge stellen darf, sind manche Löschanträge auch offensichtlich unbegründet; solche Anträge kannst du ignorieren.

Vielleicht fühlst du dich durch den Löschantrag vor den Kopf gestoßen, weil durch den Antrag die Arbeit, die Du in den Artikel gesteckt hast, nicht gewürdigt wird. [[WP:Sei tapfer|Sei tapfer]] und [[Wikipedia:Wikiquette|bleibe dennoch freundlich]]. Der andere meint es [[WP:Geh von guten Absichten aus|vermutlich auch gut]].

Ich bin übrigens nur ein [[WP:Bots|Bot]]. Wenn ich nicht richtig funktioniere, sag bitte [[Benutzer Diskussion:DerIch27|DerIch27]] bescheid. Wenn du nicht mehr von mir benachrichtigt werden möchtest, kannst du dich auf [[Benutzer:Xqbot/Opt-out:LD-Hinweis|dieser]] oder [[Benutzer:DerIchBot/Opt-Out Liste|dieser Liste]] eintragen.

Freundliche Grüsse  --~~~~"""
    elif pagetitle.startswith('Benutzer:'):
        return f"""
== [[{pagetitle}]] ==

Hallo{'' if isIP else ' '+username},

gegen die im Betreff genannte, von dir angelegte oder erheblich bearbeitete Benutzerseite wurde ein Löschantrag gestellt (nicht von mir). Bitte entnimm den Grund dafür der '''[[{deletionDiskTitle}#{sectiontitle[1:]}|Löschdiskussion]]'''. Ob die Seite tatsächlich gelöscht wird, wird sich gemäß unserer [[WP:Löschregeln|Löschregeln]] im Laufe der siebentägigen Löschdiskussion entscheiden. 

Du bist herzlich eingeladen, dich an der [[{deletionDiskTitle}#{pagetitle.replace(' ','_')}|Löschdiskussion]] zu beteiligen. Da bei Wikipedia jeder Löschanträge stellen darf, sind manche Löschanträge auch offensichtlich unbegründet; solche Anträge kannst du ignorieren.

Ich bin übrigens nur ein [[WP:Bots|Bot]]. Wenn ich nicht richtig funktioniere, sag bitte [[Benutzer Diskussion:DerIch27|DerIch27]] bescheid. Wenn du nicht mehr von mir benachrichtigt werden möchtest, kannst du dich auf [[Benutzer:Xqbot/Opt-out:LD-Hinweis|dieser]] oder [[Benutzer:DerIchBot/Opt-Out Liste|dieser Liste]] eintragen.

Freundliche Grüsse  --~~~~"""
    else:
        return f"""
== [[{pagetitle}]] ==

Hallo{'' if isIP else ' '+username},

gegen den im Betreff genannten, von dir angelegten oder erheblich bearbeiteten Artikel wurde ein Löschantrag gestellt (nicht von mir). Bitte entnimm den Grund dafür der '''[[{deletionDiskTitle}#{sectiontitle}|Löschdiskussion]]'''. Ob der Artikel tatsächlich gelöscht wird, wird sich gemäß unserer [[WP:Löschregeln|Löschregeln]] im Laufe der siebentägigen Löschdiskussion entscheiden. 

Du bist herzlich eingeladen, dich an der [[{deletionDiskTitle}#{pagetitle.replace(' ','_')}|Löschdiskussion]] zu beteiligen. Wenn du möchtest, dass der Artikel behalten wird, kannst du dort die Argumente, die für eine Löschung sprechen, entkräften, indem du dich beispielsweise zur [[Wikipedia:Relevanzkriterien|enzyklopädischen Relevanz]] des Artikels äußerst. Du kannst auch während der Löschdiskussion Artikelverbesserungen vornehmen, die die Relevanz besser erkennen lassen und die [[Wikipedia:Artikel#Mindestanforderungen|Mindestqualität]] sichern.

Da bei Wikipedia jeder Löschanträge stellen darf, sind manche Löschanträge auch offensichtlich unbegründet; solche Anträge kannst du ignorieren.

Vielleicht fühlst du dich durch den Löschantrag vor den Kopf gestoßen, weil durch den Antrag die Arbeit, die Du in den Artikel gesteckt hast, nicht gewürdigt wird. [[WP:Sei tapfer|Sei tapfer]] und [[Wikipedia:Wikiquette|bleibe dennoch freundlich]]. Der andere meint es [[WP:Geh von guten Absichten aus|vermutlich auch gut]].

Ich bin übrigens nur ein [[WP:Bots|Bot]]. Wenn ich nicht richtig funktioniere, sag bitte [[Benutzer Diskussion:DerIch27|DerIch27]] bescheid. Wenn du nicht mehr von mir benachrichtigt werden möchtest, kannst du dich auf [[Benutzer:Xqbot/Opt-out:LD-Hinweis|dieser]] oder [[Benutzer:DerIchBot/Opt-Out Liste|dieser Liste]] eintragen.

Freundliche Grüsse  --~~~~"""
        
if __name__ == '__main__':
    site = pywikibot.Site('de', 'wikipedia')
    site.login()
    handleDeletionDiscussionUpdate(site, 'Wikipedia:Löschkandidaten/18. April 2024')
