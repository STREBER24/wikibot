from typing import Any
import wikitextparser as wtp
import pywikibot
import requests
import logging
import random
import optOut
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
                logging.debug(f'skip because id is already set: {page.title()}')
                continue
            dischs = getAllSchoolDischs(page.title()) | getAllSchoolDischs(utils.findTemplateArg(template, 'Schulname'))
            if len(dischs) == 0:
                logging.info(f'skip because no disch was found: {page.title()}')
                continue
            if len(dischs) > 1:
                logging.info(f'skip because multiple dischs were found: {page.title()}')
                continue
            logging.info(f'handle {page.title()}')
            disch = dischs.pop()
            template.set_arg('Schulnummer', disch, preserve_spacing=True)
            page.text = parsed
            if optOut.isAllowed(page):
                page.save(botflag=True, minor=False, summary=(f'Bot: Ergänze Schulnummer (DISCH). Siehe https://schulamt-bw.de/Schuladressdatenbank'))

def addWikidataNumberClaim(repo: Any, item: pywikibot.ItemPage, property: str, number: int, url: str, pointInTime: pywikibot.WbTime):
    logging.info(f'try to add claim {property} to {item.title()}')
    existingClaims: list[pywikibot.Claim] = item.get()['claims'].get(property) or []
    for existingClaim in existingClaims:
        pointInTimeQualifiers: list[pywikibot.Claim] = existingClaim.qualifiers.get('P585') or []
        for qual in pointInTimeQualifiers:
            if qual.getTarget() == pointInTime:
                logging.info(f'skip update of {item.title()} because {property} is already set with same point in time qualifier.')
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
        logging.info(f'found disch {disch} of {page.title()}')
        try:
            school = getSchoolByDisch(disch)
        except Exception as e:
            logging.error(f'failed when fetching school: {e}')
        else:
            students = school.get('SCHUELER')
            teachers = school.get('LEHRER')
            item = pywikibot.ItemPage.fromPage(page)
            if students != None: addWikidataNumberClaim(repo, item, 'P2196',  students, 'https://schulamt-bw.de/Schuladressdatenbank', pywikibot.WbTime(2024, 1))
            if teachers != None: addWikidataNumberClaim(repo, item, 'P10610', teachers, 'https://schulamt-bw.de/Schuladressdatenbank', pywikibot.WbTime(2024, 1))


# .venv/bin/python src/schools-bw.py >> logs/schools.log &
if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(levelname)s - SCHOOLS BW - %(message)s', level=logging.INFO)
    # addAllDischs()
    updateWikidata()