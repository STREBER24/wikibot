from typing import Literal, Any
from datetime import datetime
import wikitextparser as wtp
import traceback
import pywikibot
import telegram
import logging
import optOut
import utils
import pytz
import time
import re

parseMonthDict = {'Januar':1, 'Jänner':1, 'January':1, 'Jan':1,
                  'Februar':2, 'February':2, 'Feb':2,
                  'März':3, 'March':3, 'Mar':3,
                  'April':4, 'Apr':4,
                  'Mai':5, 'May':5,
                  'Juni':6, 'June':6, 'Jun':6,
                  'Juli':7, 'July':7, 'Jul':7,
                  'August':8, 'Aug':8,
                  'September':9, 'Sep':9,
                  'Oktober':10, 'October':10, 'Oct':10,
                  'November':11, 'Nov':11,
                  'Dezember':12, 'December':12, 'Dec':12}

def parseWeirdDateFormats(date: str|None):
    ''' Wandelt möglichst alle Datumsformate, die die Vorlage Internetquelle akzeptiert, in Format YYYY-MM-DD um. Gibt False für ungültige Daten zurück. '''
    try:
        if type(date) is not str: return None
        date = date.replace(' ', ' ') # &nbsp;
        if re.match('^[0-9]{4}(-[0-9]{2}(-[0-9]{2}.*)?)?$', date): 
            return date[:10]
        if re.match('^[0-9]{4}-[0-9]{2}-[0-9]$', date): 
            return date.split('-')[0] + '-' + date.split('-')[1] + '-' + date.split('-')[2].rjust(2,'0')
        if re.match('^[0-9][0-9]?\\.[0-9][0-9]?\\.[0-9]{4}$', date): 
            return date.split('.')[2] + '-' + date.split('.')[1].rjust(2,'0') + '-' + date.split('.')[0].rjust(2,'0')
        if re.match('^[0-9][0-9]?\\. (Januar|Jänner|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember) [0-9]{4}$', date):
            return date.split(' ')[2] + '-' + str(parseMonthDict[date.split(' ')[1]]).rjust(2,'0') + '-' + date.split(' ')[0][:-1].rjust(2,'0')
        if re.match('^(Januar|Jänner|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember) [0-9]{4}$', date):
            return date.split(' ')[1] + '-' + str(parseMonthDict[date.split(' ')[0]]).rjust(2,'0')
        if re.match('^[0-9][0-9]? (January|February|March|April|May|June|July|August|September|October|November|December) [0-9]{4}$', date):
            return date.split(' ')[2] + '-' + str(parseMonthDict[date.split(' ')[1]]).rjust(2,'0') + '-' + date.split(' ')[0].rjust(2,'0')
        if re.match('^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December) [0-9][0-9]?, [0-9]{4}$', date):
            return date.split(', ')[1] + '-' + str(parseMonthDict[date.split(' ')[0]]).rjust(2,'0') + '-' + date.split(', ')[0].split(' ')[1].rjust(2,'0')
        if re.match('^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December) [0-9]{4}$', date):
            return date.split(' ')[1] + '-' + str(parseMonthDict[date.split(' ')[0]]).rjust(2,'0')
        return False
    except Exception as e:
        e.add_note(f'failed while parsing weird date "{date}"')
        raise e

def getTodayString():
    ''' Gibt Datum in der Form YYYY-MM-DD deutscher Zeit zurück '''
    return datetime.now(tz=pytz.timezone('Europe/Berlin')).strftime('%Y-%m-%d')

def datesOk(template: wtp.Template) -> tuple[Literal[True]|str, str|None]:
    ''' Prüft, ob Daten der Vorlagen Internetquelle, Literatur und Cite web ungültig sind oder in der Zukunft liegen '''
    templateName = template.name.strip()
    if templateName not in ['Internetquelle', 'Literatur', 'Cite web']:
        return True, None
    todayString = getTodayString()
    abruf   = parseWeirdDateFormats(utils.findTemplateArg(template, {'Internetquelle': 'abruf',   'Literatur': 'Abruf',   'Cite web': 'access-date'}[templateName]))
    zugriff = parseWeirdDateFormats(utils.findTemplateArg(template, {'Internetquelle': 'zugriff', 'Literatur': 'Zugriff', 'Cite web': 'accessdate'}[templateName]))
    datum   = parseWeirdDateFormats(utils.findTemplateArg(template, {'Internetquelle': 'datum',   'Literatur': 'Datum',   'Cite web': 'date'}[templateName]))
    if abruf == False: return 'Abrufdatum ungültig.', abruf
    if zugriff == False: return 'Zugriffsdatum ungültig.', zugriff
    if datum == False: return 'Veröffentlichungsdatum ungültig.', datum
    if datum != None and datum > todayString: return "Parameter datum liegt in der Zukunft.", datum
    if abruf == None and zugriff == None and templateName == 'Internetquelle': return "Pflichtparameter abruf nicht gesetzt.", abruf
    if abruf == None and zugriff == None and templateName != 'Internetquelle': return True, None
    if abruf != None and zugriff != None: return "Parameter abruf und zugriff beide gesetzt.", abruf
    if abruf == None: abruf = zugriff
    if abruf > todayString: return "Parameter abruf/zugriff liegt in der Zukunft.", abruf
    return True, None

def archiveParamsOk(template: wtp.Template) -> Literal[True] | str:
    ''' Prüft, ob Parameter archiv-url und archiv-datum der Vorlagen Internetquelle und Cite web konsistent sind '''
    if template.name.strip() != 'Internetquelle': return True
    if utils.findTemplateArg(template, 'titel') == None: return 'Pflichtparameter titel nicht gesetzt.'
    archivurl   = utils.findTemplateArg(template, 'archiv-url')
    archivdatum = parseWeirdDateFormats(utils.findTemplateArg(template, 'archiv-datum'))
    abrufdatum  = parseWeirdDateFormats(utils.findTemplateArg(template, 'abruf'))
    datum       = parseWeirdDateFormats(utils.findTemplateArg(template, 'datum'))
    if archivdatum == False: return 'Archivierungsdatum ungültig.'
    if abrufdatum == False or datum == False: return True # wird von datesOk abgefangen
    if archivurl == None and archivdatum == None: return True
    if archivurl == None and archivdatum != None: return True # 'Parameter archiv-datum ohne archiv-url gesetzt.'
    if archivdatum != None: archivdatum = archivdatum.replace('-', '')
    if abrufdatum  != None: abrufdatum  = abrufdatum.replace('-', '')
    if datum       != None: datum       = datum.replace('-', '')
    if not re.match('^https://web.archive.org/web/[0-9]{14}/', archivurl): return True
    if archivurl[28:36] == archivdatum or archivurl[28:36] == abrufdatum or archivurl[28:36] == datum: return True
    if archivdatum == None: return True # "Kein Archivierungsdatum gesetzt."
    return "Falsches Archivierungsdatum gesetzt."

class Problem(dict):
    def __init__(self, titel: str|None=None, problemtyp: str|None=None, snippet: str|None=None, foundDate: str|None=None, assets: Any=None, dictionary: dict = {}):
        if not isinstance(titel,       str): titel       = dictionary.get('titel')
        if not isinstance(problemtyp,  str): problemtyp  = dictionary.get('problemtyp')
        if not isinstance(snippet,     str): snippet     = dictionary.get('snippet')
        if not isinstance(foundDate,   str): foundDate   = dictionary.get('foundDate')
        if assets is None:                   assets      = dictionary.get('assets')
        freshVersion = dictionary.get('freshVersion')
        revision     = dictionary.get('revision')
        user         = dictionary.get('user')
        assert isinstance(titel, str)
        assert isinstance(problemtyp, str)
        assert isinstance(snippet, str)
        assert isinstance(foundDate, str)
        assert isinstance(freshVersion, bool) or freshVersion is None
        assert isinstance(revision, int) or revision is None
        assert isinstance(user, str) or user is None
        self.titel        = titel
        self.problemtyp   = problemtyp
        self.foundDate    = foundDate
        self.snippet      = snippet
        self.freshVersion = freshVersion
        self.revision     = revision
        self.user         = user
        self.assets       = assets
    def __str__(self):
        return self.titel + ': ' + self.problemtyp + ' ' + self.snippet
    def __eq__(self, other):
        if type(other) != Problem: return False
        if self.titel != other.titel: return False
        if self.problemtyp != other.problemtyp: return False
        if self.snippet != other.snippet: return False
        return True
    def toDict(self):
        return {'titel': self.titel, 'problemtyp': self.problemtyp, 'snippet': self.snippet, 'foundDate': self.foundDate, 'revision': self.revision, 'freshVersion': self.freshVersion, 'assets': self.assets, 'user': self.user}

def loadAllProblems() -> list[Problem]:
    content: list[dict] = utils.loadJson('data/problems.json', [])
    return  [Problem(dictionary=problem) for problem in content]

def dumpAllProblems(allProblems: list[Problem]):
    content = [problem.toDict() for problem in allProblems]
    utils.dumpJson('data/problems.json', content)

def checkPageContent(titel: str, content: str, todayString: str):
    for template in wtp.parse(content).templates:
        result, asset = datesOk(template)
        if True != result: 
            yield Problem(titel, result, str(template), todayString, asset)
        result = archiveParamsOk(template)
        if True != result: 
            yield Problem(titel, result, str(template), todayString)

def checkPage(site: Any, pagetitle: str, allProblems: list[Problem], previousServerErrors: int=0):
    try:
        page = pywikibot.Page(site, pagetitle)
        content = page.get()
        for problem in checkPageContent(page.title(), content, getTodayString()):
            if problem in allProblems: continue
            for rev in page.revisions(total=50):
                try:
                    if rev['parentid'] == 0: problem.revision = rev['revid']; break
                    oldContent = page.getOldVersion(rev['parentid'])
                    if oldContent == None: break # Version verborgen
                    oldProblems = list(checkPageContent(page.title(), oldContent, getTodayString()))
                    if problem not in oldProblems:
                        problem.freshVersion = (oldProblems == [])
                        problem.revision = rev['revid']
                        problem.user = rev['user']
                        break
                except Exception as e:
                    e.add_note(f'failed while checking if problem already existed before revision {rev.get('revid')}')
                    raise e
            logging.info(f'Problem: {problem}')
            yield problem
    except pywikibot.exceptions.IsRedirectPageError:
        return
    except pywikibot.exceptions.NoPageError:
        return
    except pywikibot.exceptions.ServerError as e:
        e.add_note(f'failed while checking page {pagetitle}')
        if previousServerErrors <= 4:
            logging.warning(f'Ignored Server Error\n{traceback.format_exc()}')
            telegram.send('WARNING: Ignored Server Error')
            return checkPage(site, pagetitle, allProblems, previousServerErrors+1)
        else:
            e.add_note(f'failed after {previousServerErrors+1} server errors')
            raise e
    except Exception as e:
        e.add_note(f'failed while checking page {pagetitle}')
        raise e

def checkPagesInProblemList(site):
    allProblems = loadAllProblems()
    logging.debug(f'checking list of {len(allProblems)} problems ...')
    site.login()
    index = 0
    allPages = set()
    previousServerErrors = 0
    while index < len(allProblems):
        problem = allProblems[index]
        allPages.add(problem.titel)
        page = pywikibot.Page(site, problem.titel)
        try:
            content = page.text
        except pywikibot.exceptions.NoPageError:
            logging.debug(f'Artikel {problem.titel} verschwunden.')
            del allProblems[index]
            continue
        except pywikibot.exceptions.ServerError as e:
            previousServerErrors += 1
            if previousServerErrors <= 4:
                logging.warning(f'Ignored Server Error\n{traceback.format_exc()}')
                telegram.send('WARNING: Ignored Server Error')
                continue
            else:
                e.add_note(f'failed after {previousServerErrors+1} server errors')
                raise e
        if problem in checkPageContent(problem.titel, content, problem.foundDate): 
            index += 1
        else:
            logging.debug(f'Problem in {problem.titel} abgearbeitet.')
            del allProblems[index]
    for page in allPages:
        allProblems += checkPage(site, page, allProblems)
    dumpAllProblems(allProblems)
    
def updateWikilist():
    allProblems = loadAllProblems()
    datum = None
    titel = None
    wikitext = '{{/Info|' + str(len(allProblems)) + '|' + getTodayString() + '}}\n\n'
    for problem in allProblems:
        if datum != problem.foundDate:
            wikitext += f'== {utils.formatDateFromDatestring(problem.foundDate)} ==\n\n'
        if titel != problem.titel or datum != problem.foundDate:
            wikitext += '{{Überschriftensimulation|3|Text=[[' + problem.titel + ']]}}\n'
        wikitext += f'{problem.problemtyp}{'' if problem.revision==None else f' ([[Spezial:Diff/{problem.revision}|Änderung]]{'' if problem.freshVersion else ' ???'})'}\n'
        wikitext += f'<pre>{problem.snippet}</pre>\n\n'
        datum = problem.foundDate
        titel = problem.titel
    site = pywikibot.Site('de', 'wikipedia')
    site.login()
    page = pywikibot.Page(site, 'Benutzer:DerIchBot/Wartungsliste')
    page.text = wikitext
    site.login()
    if optOut.isAllowed(page):
        page.save(botflag=True, minor=False, summary=(f'Bot: Aktualisiere Wartungsliste: {len(allProblems)} Einträge'))
    site.logout()
    
numberOfChanges = 0
numberOfNewProblems = 0
def checkPagefromRecentChanges(site: Any, pagetitle: str):
    global numberOfNewProblems
    global numberOfChanges
    numberOfChanges += 1
    allProblems = loadAllProblems()
    newProblems = checkPage(site, pagetitle, allProblems)
    for problem in newProblems:
        numberOfNewProblems += 1
        if re.match('Parameter (datum|abruf/zugriff) liegt in der Zukunft\\.', problem.problemtyp) and problem.freshVersion:
            futureWarnings: list[str] = utils.loadJson('data/futureWarningsPlanned.json', [])
            if problem.titel not in futureWarnings: futureWarnings.append(problem.titel)
            utils.dumpJson('data/futureWarningsPlanned.json', futureWarnings)
        if len(allProblems) < 300 and problem not in allProblems:
            allProblems.append(problem)
    dumpAllProblems(allProblems)
    if numberOfChanges >= 200:
        logging.info(f'Checked 200 changes and found {numberOfNewProblems} new problems.')
        numberOfNewProblems = 0
        numberOfChanges = 0

def sendPlannedNotifications(site):
    plannedNotifications: list[str] = utils.loadJson('data/futureWarningsPlanned.json', [])
    sentNotifications: dict[str, dict[str, str]] = utils.loadJson('data/futureWarningsSent.json', {})
    skippedNotifications: set[str] = set()
    outgoingNotifications: dict[str, set[str]] = {}
    for pagetitle in plannedNotifications:
        logging.info(f'check page "{pagetitle}" to notifications on cite param problems ...')
        timeSinceLastRevision = (time.time() - pywikibot.Page(site, pagetitle).latest_revision['timestamp'].timestamp()) / 3600
        logging.debug(f'time since latest revision on {pagetitle}: {timeSinceLastRevision:.2f}h')
        if timeSinceLastRevision < 6:
            logging.info(f'skip problem notification on "{pagetitle}" because latest revision is too new')
            skippedNotifications.add(pagetitle)
            continue
        for problem in checkPage(site, pagetitle, []):
            if not re.match('Parameter (datum|abruf/zugriff) liegt in der Zukunft\\.', problem.problemtyp): continue
            if not problem.freshVersion: continue
            if sentNotifications.get(problem.user) == None: sentNotifications[problem.user] = {}
            if sentNotifications[problem.user].get(pagetitle) != None: 
                logging.info(f'skip notification of {problem.user} on "{pagetitle}" because already notified on {sentNotifications[problem.user][pagetitle]}')
                continue
            logging.debug(problem.toDict())
            if outgoingNotifications.get(problem.user) == None: outgoingNotifications[problem.user] = set()
            datumstyp = 'Veröffentlichungsdatum' if problem.problemtyp.startswith('Parameter datum') else 'Abrufdatum'
            outgoingNotifications[problem.user].add(f'Du hast mit [[Spezial:Diff/{problem.revision}|dieser Änderung]] auf [[{pagetitle}]] den {utils.formatDateFromDatestring(problem.assets)} als {datumstyp} angegeben. Da dieses Datum in der Zukunft liegt, möchte ich dich bitten, deine Änderung nochmal auf Tippfehler zu überprüfen.')
            sentNotifications[problem.user][pagetitle] = getTodayString()
    for user, messages in outgoingNotifications.items():
        messageList = list(messages)
        messageList[0] = messageList[0][0].lower() + messageList[0][1:]
        completeMessage = utils.formatUserInfo('Möglicherweise fehlerhafte Datumsangabe', user, '\n\n'.join(messageList))
        userdisk = pywikibot.Page(site, f'Benutzer Diskussion:{user}')
        userdisk.text += completeMessage
        if utils.savePage(userdisk, f'Informiere über potentiell fehlerhafte Datumsangabe', botflag=True):
            logging.info(f'Notify {user} about cite param problem')
        else:
            logging.info(f'do not notify {user} because saving failed')
    utils.dumpJson('data/futureWarningsPlanned.json', list(skippedNotifications))
    utils.dumpJson('data/futureWarningsSent.json', sentNotifications)

if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(levelname)s - CITE PARAMS - %(message)s', level=logging.DEBUG)
    site = pywikibot.Site('de', 'wikipedia')
    sendPlannedNotifications(site)