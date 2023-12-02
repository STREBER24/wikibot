import wikitextparser as wtp
import pywikibot
import requests
import random
import utils
import time
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
                data.add(school.get('DISCH').strip("'"))
            pageNumber += 1
            if not multiplePages: ok = False
        except AssertionError:
            ok = False
    return data

def run():
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
            time.sleep(5)
            input('press enter to continue ...')

if __name__ == '__main__':
    run()