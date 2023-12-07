from pywikibot import pagegenerators as pg
import wikitextparser as wtp
import pywikibot
import time
import json
import bs4
import io

def getText(tag: bs4.Tag | str | None) -> str:
    if tag == None: return ''
    if type(tag) == bs4.Tag: tag = tag.text
    return tag.strip().replace('  ', ' ')

def formatDate(day: str|int, month: str|int, year: str|int):
    months = ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember']
    return f'{day}. {months[int(month)-1]} {year}'

def getTemplateUsage(site: pywikibot.BaseSite, tmpl_name: str):
    print(f'[INFO] checking usage of template {tmpl_name} ...', end=' ')
    name = "{}:{}".format(site.namespace(10), tmpl_name)
    tmpl_page = pywikibot.Page(site, name)
    ref_gen = tmpl_page.getReferences(follow_redirects=False)
    filter_gen = pg.NamespaceFilterPageGenerator(ref_gen, namespaces=[0])
    generator = site.preloadpages(filter_gen, pageprops=True)
    print('finished')
    return generator

def findTemplateArg(template: wtp.Template, argName: str):
    argument = template.get_arg(argName)
    if argument == None: return None
    stripped = wtp.parse(argument.value).plain_text().strip()
    return stripped if stripped != '' else None

def checkLastUpdate(key: str, minDelayDays: int):
    try:
        with io.open('last-updates.json', encoding='utf8') as file:
            data: dict = json.load(file)
    except:
        data = dict()
    if data.get(key) != None and data.get(key) > time.time() - (minDelayDays*60*60*24):
        return False
    data[key] = int(time.time())
    with io.open('last-updates.json', 'w', encoding='utf8') as file:
            json.dump(data, file)
    return True

def addWikidataSource(repo: any, claim: pywikibot.Claim,  url: str):
    now = time.localtime()
    today = pywikibot.WbTime(year=now.tm_year, month=now.tm_mon, day=now.tm_mday)
    ref = pywikibot.Claim(repo, 'P854')
    ref.setTarget(url)
    retrieved = pywikibot.Claim(repo, 'P813')
    retrieved.setTarget(today) 
    claim.addSources([ref, retrieved], summary=f'Bot: Adding references.')
