from pywikibot.comms import eventstreams
from typing import Literal, Any
from datetime import datetime
import wikitextparser as wtp
import deletionInfo
import pywikibot
import traceback
import telegram
import logging
import katdisk
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
        return False
    except Exception as e:
        e.add_note(f'failed while parsing weird date "{date}"')
        raise e

def getTodayString():
    ''' Gibt Datum in der Form YYYY-MM-DD deutscher Zeit zurück '''
    return datetime.now(tz=pytz.timezone('Europe/Berlin')).strftime('%Y-%m-%d')

def datesOk(template: wtp.Template) -> Literal[True] | str:
    ''' Prüft, ob Daten der Vorlagen Internetquelle, Literatur und Cite web in der Zukunft liegen '''
    templateName = template.name.strip()
    if templateName not in ['Internetquelle', 'Literatur', 'Cite web']:
        return True
    todayString = getTodayString()
    abruf   = parseWeirdDateFormats(utils.findTemplateArg(template, {'Internetquelle': 'abruf',   'Literatur': 'Abruf',   'Cite web': 'access-date'}[templateName]))
    zugriff = parseWeirdDateFormats(utils.findTemplateArg(template, {'Internetquelle': 'zugriff', 'Literatur': 'Zugriff', 'Cite web': 'accessdate'}[templateName]))
    datum   = parseWeirdDateFormats(utils.findTemplateArg(template, {'Internetquelle': 'datum',   'Literatur': 'Datum',   'Cite web': 'date'}[templateName]))
    if abruf == False: return 'Abrufdatum ungültig.'
    if zugriff == False: return 'Zugriffsdatum ungültig.'
    if datum == False: return 'Veröffentlichungsdatum ungültig.'
    if datum != None and datum > todayString: return "Parameter datum liegt in der Zukunft."
    if abruf == None and zugriff == None and templateName == 'Internetquelle': return "Pflichtparameter abruf nicht gesetzt."
    if abruf == None and zugriff == None and templateName != 'Internetquelle': return True
    if abruf != None and zugriff != None: return "Parameter abruf und zugriff beide gesetzt."
    if abruf == None: abruf = zugriff
    if abruf > todayString: return "Parameter abruf/zugriff liegt in der Zukunft."
    return True

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
    def __init__(self, titel: str|None=None, problemtyp: str|None=None, snippet: str|None=None, foundDate: str|None=None, dictionary: dict = {}):
        if not isinstance(titel,      str): titel      = dictionary.get('titel')
        if not isinstance(problemtyp, str): problemtyp = dictionary.get('problemtyp')
        if not isinstance(snippet,    str): snippet    = dictionary.get('snippet')
        if not isinstance(foundDate,  str): foundDate  = dictionary.get('foundDate')
        assert isinstance(titel, str);      self.titel      = titel
        assert isinstance(problemtyp, str); self.problemtyp = problemtyp
        assert isinstance(snippet, str);    self.snippet    = snippet
        assert isinstance(foundDate, str);  self.foundDate  = foundDate
        self.revision: int|None = dictionary.get('revision')
    def __str__(self):
        return self.titel + ': ' + self.problemtyp + ' ' + self.snippet
    def __eq__(self, other):
        if type(other) != Problem: return False
        if self.titel != other.titel: return False
        if self.problemtyp != other.problemtyp: return False
        if self.snippet != other.snippet: return False
        return True
    def toDict(self):
        return {'titel': self.titel, 'problemtyp': self.problemtyp, 'snippet': self.snippet, 'foundDate': self.foundDate, 'revision': self.revision}

def loadAllProblems() -> list[Problem]:
    content: list[dict] = utils.loadJson('data/problems.json', [])
    return  [Problem(dictionary=problem) for problem in content]

def dumpAllProblems(allProblems: list[Problem]):
    content = [problem.toDict() for problem in allProblems]
    utils.dumpJson('data/problems.json', content)

def checkPageContent(titel: str, content: str, todayString: str):
    for template in wtp.parse(content).templates:
        result = datesOk(template)
        if True != result: 
            yield Problem(titel, result, str(template), todayString)
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
                    if problem not in checkPageContent(page.title(), oldContent, getTodayString()): 
                        problem.revision = rev['revid']
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

DELAY_THRESHOLD = 300 # 5min
class LagMonitor:
    def __init__(self):
        self.lastLagNotification: float = 0
        self.numberOfDelayedChanges = 0
        self.maxLag = 0
        self.minLag = 9999999999999999
        self.firstLag: float = 0
    def formatSeconds(self, timediff: int):
        result = f'{timediff%60} s'; timediff = timediff // 60
        if timediff == 0: return result
        result = f'{timediff%60} min, {result}'; timediff = timediff // 60
        if timediff == 0: return result
        result = f'{timediff%24} h, {result}'; timediff = timediff // 24
        if timediff == 0: return result
        return f'{timediff} d, {result}'
    def checkRevision(self, change: dict):
        lag = int(time.time() - change['timestamp'])
        if lag > DELAY_THRESHOLD and self.maxLag <= DELAY_THRESHOLD: self.firstLag = time.time()
        if lag > self.maxLag: self.maxLag = lag
        if lag < self.minLag: self.minLag = lag
        if lag > DELAY_THRESHOLD:
            logging.warning(f'Handled revision {change.get('revision')} with delay of {lag}s')
            self.numberOfDelayedChanges += 1
        if (self.maxLag > DELAY_THRESHOLD) and (time.time() - self.lastLagNotification > 600) and (time.time() - self.firstLag > 300):
            telegram.send(f'LAG WARNING\nminimum: {self.formatSeconds(self.minLag)}\nmaximum: {self.formatSeconds(self.maxLag)}\n{self.numberOfDelayedChanges} delayed changes', silent=True)
            self.numberOfDelayedChanges = 0
            self.lastLagNotification = time.time()
            self.maxLag = 0
            self.minLag = 9999999999999999

def monitorRecentChanges():
    allProblems = loadAllProblems()
    site = pywikibot.Site('de', 'wikipedia')
    stream = eventstreams.EventStreams(streams='recentchange')
    site.login()
    stream.register_filter(type='edit', wiki='dewiki')
    numberOfChanges = 0
    numberOfProblemsBefore = len(allProblems)
    lagMonitor = LagMonitor()
    while True:
        try:
            change = next(stream)
            logging.debug(f'handle recent change {change.get('revision')} on {change.get('title')}')
            lagMonitor.checkRevision(change)
            telegram.alarmOnChange(change)
            if change['namespace'] == 4: # Wikipedia:XYZ
                if re.match('^Wikipedia:Löschkandidaten/.', change['title']):
                    deletionInfo.handleDeletionDiscussionUpdate(site, change['title'], change)
                if re.match('^Wikipedia:WikiProjekt Kategorien/Diskussionen/[0-9]{4}/(Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)/[0-9][0-9]?$', change['title']):
                    katdisk.handleKatDiscussionUpdate(site, change['title'])
            elif change['namespace'] == 0: # Artikelnamensraum
                if len(allProblems) >= 300:
                    if utils.checkLastUpdate('check-problems-list-full', 90):
                        checkPagesInProblemList()
                        allProblems = loadAllProblems()
                else:
                    numberOfChanges += 1
                    allProblems = loadAllProblems()
                    allProblems += checkPage(site, change['title'], allProblems)
                    dumpAllProblems(allProblems)
                    if numberOfChanges >= 100:
                        logging.info(f'Checked 100 changes and found {len(allProblems)-numberOfProblemsBefore} problems.')
                        numberOfProblemsBefore = len(allProblems)
                        numberOfChanges = 0
        except Exception as e:
            e.add_note(f'failed while handling recent change {change.get('revision')} on {change.get('title')}')
            raise e

def checkPagesInProblemList():
    allProblems = loadAllProblems()
    logging.debug(f'checking list of {len(allProblems)} problems ...')
    site = pywikibot.Site('de', 'wikipedia')
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
    wikitext = '{{/Info|' + str(len(allProblems)) + '}}\n\n'
    for problem in allProblems:
        if datum != problem.foundDate:
            wikitext += f'== {utils.formatDate(int(problem.foundDate[8:10]), problem.foundDate[5:7], problem.foundDate[0:4])} ==\n\n'
        if titel != problem.titel or datum != problem.foundDate:
            wikitext += '{{Überschriftensimulation|3|Text=[[' + problem.titel + ']]}}\n'
        wikitext += f'{problem.problemtyp}{'' if problem.revision==None else f' ([[Spezial:Diff/{problem.revision}|Änderung]])'}\n'
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

def run():
    checkPagesInProblemList()
    updateWikilist()
    monitorRecentChanges()

if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(levelname)s - RECENT CHANGES - %(message)s', level=logging.INFO)
    telegram.send('start recent changes service ...', silent=True)
    try:
        monitorRecentChanges()
    except KeyboardInterrupt:
        print('Exception: KeyboardInterrupt')
    except Exception as e:
        telegram.handleException()
            