from pywikibot.comms import eventstreams
from datetime import datetime
import wikitextparser as wtp
from typing import Literal, Any
import pywikibot
import traceback
import utils
import json
import time
import re
import io

def parseWeirdDateFormats(date: str|None):
    ''' Wandelt möglichst alle Datumsformate, die die Vorlage Internetquelle akzeptiert in Format YYYY-MM-DD um '''
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
            return date.split(' ')[2] + '-' + str({'Januar':1, 'Jänner':1,'Februar':2,'März':3,'April':4,'Mai':5,'Juni':6,'Juli':7,'August':8,'September':9,'Oktober':10,'November':11,'Dezember':12}[date.split(' ')[1]]).rjust(2,'0') + '-' + date.split(' ')[0][:-1].rjust(2,'0')
        if re.match('^[0-9][0-9]? (January|February|March|April|May|June|July|August|September|October|November|December) [0-9]{4}$', date):
            return date.split(' ')[2] + '-' + str(['January','February','March','April','May','June','July','August','September','October','November','December'].index(date.split(' ')[1])+1).rjust(2,'0') + '-' + date.split(' ')[0].rjust(2,'0')
        return None
    except Exception as e:
        e.add_note(f'failed while parsing weird date "{date}"')
        raise e

def getTodayString():
    return datetime.now().strftime('%Y-%m-%d')

def datesOk(template: wtp.Template) -> Literal[True] | str:
    ''' Prüft, ob Daten der Vorlagen Internetquelle und Literatur in der Zukunft liegen '''
    if template.name.strip() not in ['Internetquelle', 'Literatur']:
        return True
    todayString = getTodayString()
    isInternetquelle = template.name.strip() == 'Internetquelle'
    abruf   = parseWeirdDateFormats(utils.findTemplateArg(template, 'abruf'  if isInternetquelle else 'Abruf'))
    zugriff = parseWeirdDateFormats(utils.findTemplateArg(template, 'zugriff'if isInternetquelle else 'Zugriff'))
    datum   = parseWeirdDateFormats(utils.findTemplateArg(template, 'datum'  if isInternetquelle else 'Datum'))
    if abruf == None and zugriff == None and isInternetquelle: return "Pflichtparameter abruf nicht gesetzt."
    if abruf == None and zugriff == None and not isInternetquelle: return True
    if abruf != None and zugriff != None: return "Parameter abruf und zugriff beide gesetzt."
    if abruf == None: abruf = zugriff
    if abruf > todayString: return "Parameter abruf/zugriff liegt in der Zukunft."
    if datum != None and datum > todayString: return "Parameter datum liegt in der Zukunft."
    return True

def archiveParamsOk(template: wtp.Template) -> Literal[True] | str:
    ''' Prüft, ob Parameter archiv-url und archiv-datum der Vorlage Internetquelle konsistent sind '''
    if template.name.strip() != 'Internetquelle': return True
    if utils.findTemplateArg(template, 'titel') == None: return 'Pflichtparameter titel nicht gesetzt.'
    archivurl   = utils.findTemplateArg(template, 'archiv-url')
    archivdatum = parseWeirdDateFormats(utils.findTemplateArg(template, 'archiv-datum'))
    abrufdatum  = parseWeirdDateFormats(utils.findTemplateArg(template, 'abruf'))
    datum       = parseWeirdDateFormats(utils.findTemplateArg(template, 'datum'))
    if archivurl == None and archivdatum == None: return True
    if archivurl == None and archivdatum != None: return "Parameter archiv-datum ohne Parameter archiv-url gesetzt."
    if archivdatum != None: archivdatum = archivdatum.replace('-', '')
    if abrufdatum  != None: abrufdatum  = abrufdatum.replace('-', '')
    if datum       != None: datum       = datum.replace('-', '')
    if not re.match('^https://web.archive.org/web/[0-9]{14}/', archivurl): return True
    if archivurl[28:36] == archivdatum or archivurl[28:36] == abrufdatum or archivurl[28:36] == datum: return True
    if archivdatum == None: return "Kein Archivierungsdatum gesetzt."
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
    utils.ensureDir('data/problems.json')
    try:
        with io.open('data/problems.json', encoding='utf8') as file:
            allProblems: list[dict] = json.load(file)
        return [Problem(dictionary=problem) for problem in allProblems]
    except FileNotFoundError:
        return []

def dumpAllProblems(allProblems: list[Problem]):
    with io.open('data/problems.json', 'w', encoding='utf8') as file:
        json.dump([problem.toDict() for problem in allProblems], file, ensure_ascii=False, indent=2)

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
            print('Problem:', problem)
            yield problem
    except pywikibot.exceptions.IsRedirectPageError:
        return
    except pywikibot.exceptions.NoPageError:
        return
    except pywikibot.exceptions.ServerError as e:
        e.add_note(f'failed while checking page {pagetitle}')
        if previousServerErrors >= 4:
            print(f'WARNING: Ignored Server Error\n{traceback.format_exc()}')
            utils.sendTelegram(f'WARNING: Ignored Server Error\n{traceback.format_exc()}')
            return checkPage(site, pagetitle, allProblems, previousServerErrors+1)
        else:
            e.add_note(f'failed after {previousServerErrors+1} server errors')
            raise e
    except Exception as e:
        e.add_note(f'failed while checking page {pagetitle}')
        raise e

def monitorRecentChanges():
    allProblems = loadAllProblems()
    stream = eventstreams.EventStreams(streams='recentchange')
    site = pywikibot.Site('de', 'wikipedia')
    stream.register_filter(type='edit', wiki='dewiki', namespace=0)
    numberOfChanges = 0
    numberOfProblemsBefore = len(allProblems)
    while True:
        try:
            change = next(stream)
            numberOfChanges += 1
            allProblems = loadAllProblems()
            allProblems += checkPage(site, change['title'], allProblems)
            dumpAllProblems(allProblems)
            if numberOfChanges >= 100:
                print(f'Checked 100 changes and found {len(allProblems)-numberOfProblemsBefore} problems.')
                numberOfProblemsBefore = len(allProblems)
                numberOfChanges = 0
                while len(allProblems) >= 200:
                    if utils.checkLastUpdate('check-problems-list-full', 90):
                        checkPagesInProblemList()
                        allProblems = loadAllProblems()
                    else:
                        time.sleep(180)
                    
        except Exception as e:
            e.add_note(f'failed while handling recent change {change.get('revision')}')
            raise e

def checkPagesInProblemList():
    allProblems = loadAllProblems()
    print(f'checking list of {len(allProblems)} problems ...')
    site = pywikibot.Site('de', 'wikipedia')
    index = 0
    allPages = set()
    while index < len(allProblems):
        problem = allProblems[index]
        allPages.add(problem.titel)
        page = pywikibot.Page(site, problem.titel)
        if problem in checkPageContent(problem.titel, page.get(), problem.foundDate): 
            index += 1
        else:
            print('Problem in', problem.titel, 'abgearbeitet.')
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
            wikitext += f'== {utils.formatDate(problem.foundDate[8:10], problem.foundDate[5:7], problem.foundDate[0:4])} ==\n\n'
        if titel != problem.titel or datum != problem.foundDate:
            wikitext += '{{Überschriftensimulation|3|Text=[[' + problem.titel + ']]}}\n'
        wikitext += f'{problem.problemtyp}{'' if problem.revision==None else f' ([[Spezial:Diff/{problem.revision}|Änderung]])'}\n'
        wikitext += f'<pre>{problem.snippet}</pre>\n\n'
        datum = problem.foundDate
        titel = problem.titel
    site = pywikibot.Site('de', 'wikipedia')
    page = pywikibot.Page(site, 'Benutzer:DerIchBot/Wartungsliste')
    page.text = wikitext
    site.login()
    page.save(botflag=True, minor=False, summary=(f'Bot: Aktualisiere Wartungsliste: {len(allProblems)} Einträge'))
    site.logout()

def run():
    checkPagesInProblemList()
    updateWikilist()
    monitorRecentChanges()

if __name__ == '__main__':
    try:
        run()
    except KeyboardInterrupt:
        print('Exception: KeyboardInterrupt')
    except Exception as e:
        utils.sendTelegram(traceback.format_exc())
        raise e
            