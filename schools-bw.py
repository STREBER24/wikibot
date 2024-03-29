from typing import Any
import wikitextparser as wtp
import pywikibot
import requests
import random
import utils
import json

def getAllSchoolDischs(search: str|None='', multiplePages: bool=False) -> set[str]:
    if search == None: return set()
    uid = random.randint(1, 99999999)
    data: set[str] = set()
    ok = True
    pageNumber = 1
    url = 'https://lobw.kultus-bw.de/didsuche/DienststellenSucheWebService.asmx/SearchDienststellen'
    while ok:
        try:
            query = {'command': 'QUICKSEARCH', 'data': {'dscSearch': search, 'dscPlz': '', 'dscOrt': '', 'dscDienststellenname': '', 'dscSchulartenSelected': '', 'dscSchulstatusSelected': '', 'dscSchulaufsichtSelected': '',
                                                        'dscOrtSelected': '', 'dscEntfernung': '', 'dscAusbildungsSchulenSelected': '', 'dscAusbildungsSchulenSelectedSart': '', 'dscPageNumber': str(pageNumber), 'dscPageSize': '1000', 'dscUnique': str(uid)}}
            res = requests.post(url, json={'json': json.dumps(query)})
            assert res.ok
            rows: list[dict[str, str]] = json.loads(
                res.json().get('d')).get('Rows')
            assert len(rows) > 0
            for school in rows:
                data.add(school['DISCH'].strip("'"))
            pageNumber += 1
            if not multiplePages: ok = False
        except AssertionError:
            ok = False
    return data

def getSchoolByDisch(disch: str):
    url = 'https://lobw.kultus-bw.de/didsuche/DienststellenSucheWebService.asmx/GetDienststelle'
    res = requests.post(url, json={'disch': disch})
    data: dict = json.loads(res.json().get('d'))
    data['NAME'] = utils.getText(data.get('NAME'))
    data['UEBERGEORDNET'] = utils.getText(data.get('UEBERGEORDNET'))
    return data

def addAllDischs():
    site = pywikibot.Site('de', 'wikipedia')
    site.login()
    generator = utils.getTemplateUsage(site, 'Infobox Schule')
    for page in generator:
        parsed = wtp.parse(page.get())
        for template in parsed.templates:
            if template.name.strip() != 'Infobox Schule': continue
            if utils.findTemplateArg(template, 'Region-ISO') != 'DE-BW': continue
            currentID = utils.findTemplateArg(template, 'Schulnummer')
            if currentID not in [None, '']:
                print(f'skip because id is already set: {page.title()}')
                continue
            dischs = getAllSchoolDischs(page.title()) | getAllSchoolDischs(utils.findTemplateArg(template, 'Schulname'))
            if len(dischs) == 0:
                print(f'skip because no disch was found: {page.title()}')
                continue
            if len(dischs) > 1:
                print(f'skip because multiple dischs were found: {page.title()}')
                continue
            print(f'handle {page.title()}')
            disch = dischs.pop()
            template.set_arg('Schulnummer', disch, preserve_spacing=True)
            page.text = parsed
            page.save(botflag=True, minor=False, summary=(f'Bot: Ergänze Schulnummer (DISCH). Siehe km-bw.de/Schuladressdatenbank'))

def addWikidataNumberClaim(repo: Any, item: pywikibot.ItemPage, property: str, number: int, url: str, pointInTime: pywikibot.WbTime):
    if property in item.get()['claims']:
        print(f'skip update of {item.title()} because {property} is already set.')
        return
    # Anzahl der Schüler / Studenten / Lehrer
    claim = pywikibot.Claim(repo, property)
    claim.setTarget(pywikibot.WbQuantity(number, site=repo))
    item.addClaim(claim, summary=f'Bot: Adding claim {property}.')
    # Zeitpunkt / Stand
    qualifier = pywikibot.Claim(repo, 'P585')
    qualifier.setTarget(pointInTime)
    claim.addQualifier(qualifier, summary=f'Bot: Adding a qualifier to {property}.')
    # URL der Fundstelle und abgerufen am
    utils.addWikidataSource(repo, claim, url)

def updateWikidata():
    wikipedia = pywikibot.Site('de', 'wikipedia')
    wikidata = pywikibot.Site('wikidata', 'wikidata')
    repo = wikidata.data_repository()
    wikidata.login()
    generator = utils.getTemplateUsage(wikipedia, 'Infobox Schule')
    for page in generator:
        parsed = wtp.parse(page.get())
        ids = set()
        for template in parsed.templates:
            if template.name.strip() != 'Infobox Schule': continue
            if utils.findTemplateArg(template, 'Region-ISO') != 'DE-BW': continue
            id = utils.findTemplateArg(template, 'Schulnummer')
            if id != None: ids.add(id)
        if len(ids) != 1: continue
        disch = ids.pop()
        print(f'found disch {disch} of {page.title()}')
        try:
            school = getSchoolByDisch(disch)
        except Exception as e:
            print(f'[ERROR] when fetching school: {e}')
        else:
            students = school.get('SCHUELER')
            teachers = school.get('LEHRER')
            item = pywikibot.ItemPage.fromPage(page)
            if students != None: addWikidataNumberClaim(repo, item, 'P2196',  students, 'https://km-bw.de/Schuladressdatenbank', pywikibot.WbTime(2023, 1))
            if teachers != None: addWikidataNumberClaim(repo, item, 'P10610', teachers, 'https://km-bw.de/Schuladressdatenbank', pywikibot.WbTime(2023, 1))

if __name__ == '__main__':
    # addAllDischs()
    updateWikidata()