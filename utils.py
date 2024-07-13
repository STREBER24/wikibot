from pywikibot import pagegenerators as pg
import wikitextparser as wtp
from typing import Any, TypeVar
import pywikibot
import logging
import optOut
import time
import json
import bs4
import io
import os
import re

def getText(tag: bs4.Tag | str | None) -> str:
    if type(tag) is bs4.Tag: 
        text = tag.text
    elif type(tag) is str:
        text = tag
    else: 
        return ''
    return text.strip().replace('  ', ' ')

def formatDate(day: str|int, month: str|int, year: str|int):
    months = ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember']
    daystring = f'{int(day)}. ' if day != '' else ''
    monthstring = months[int(month)-1]+' ' if month != '' else ''
    return daystring + monthstring + str(year)

def formatDateFromDatestring(datestring: str):
    return formatDate(datestring[8:10], datestring[5:7], datestring[0:4])
    
def getTemplateUsage(site: pywikibot.Site, tmpl_name: str):
    print(f'[INFO] checking usage of template {tmpl_name} ...', end=' ')
    name = "{}:{}".format(site.namespace(10), tmpl_name)
    tmpl_page = pywikibot.Page(site, name)
    ref_gen = tmpl_page.getReferences(follow_redirects=False)
    filter_gen = pg.NamespaceFilterPageGenerator(ref_gen, namespaces=[0])
    generator = site.preloadpages(filter_gen, pageprops=True)
    print('finished')
    return generator

def templateToPlainText(template: wtp.Template):
    if template.name == 'lang':
        return findTemplateArg(template, '2')
    return str(template)

def findTemplateArg(template: wtp.Template, argName: str):
    argument = template.get_arg(argName)
    if argument == None: return None
    parsed = wtp.parse(argument.value)
    stripped = parsed.plain_text(replace_templates=templateToPlainText).strip()
    return stripped if stripped != '' else None

def checkLastUpdate(key: str, minDelayMinutes: int):
    data: dict[str,int] = loadJson('data/last-updates.json', {})
    lastUpdate = data.get(key)
    if type(lastUpdate) is int and lastUpdate > time.time() - (minDelayMinutes*60):
        return False
    data[key] = int(time.time())
    dumpJson('data/last-updates.json', data)
    return True

def addWikidataSource(repo: Any, claim: pywikibot.Claim,  url: str):
    now = time.localtime()
    today = pywikibot.WbTime(year=now.tm_year, month=now.tm_mon, day=now.tm_mday)
    ref = pywikibot.Claim(repo, 'P854')
    ref.setTarget(url)
    retrieved = pywikibot.Claim(repo, 'P813')
    retrieved.setTarget(today) 
    claim.addSources([ref, retrieved], summary=f'Bot: Adding references.')

def ensureDir(file: str):
    dir = os.path.dirname(file)
    if not os.path.isdir(dir):
        os.mkdir(dir)
        print(f'created directory {dir}')

T = TypeVar("T")
def loadJson(path: str, defaultValue: T) -> T:
    try:
        with io.open(path, encoding='utf8') as file:
            return json.load(file)
    except FileNotFoundError:
        return defaultValue

def dumpJson(path: str, content):
    ensureDir(path)
    with io.open(path, 'w', encoding='utf8') as file:
        json.dump(content, file, indent=2, ensure_ascii=False)

def savePage(page: pywikibot.Page, summary: str, botflag: bool):
    if not optOut.isAllowed(page):
        return False
    try:
        page.save(summary=f'Bot: {summary}', minor=False, botflag=botflag)
        return True
    except pywikibot.exceptions.LockedPageError:
        return False

def isBlockedForInfinity(site, username: str):
    for i in site.blocks(total=1, reverse=True, users=username):
        if i.get('expiry') == 'infinity':
            logging.debug(f'{username} is blocked for infinity')
            return True
    return False

def extractUserLinks(sec: wtp.Section):
    return set([':'.join(link.target.split(':')[1:]) for link in sec.wikilinks if re.match('^(benutzer|benutzer diskussion|bd|user|user talk):', link.target.lower())]+
               [findTemplateArg(template, '1') for template in sec.templates if template.name.strip().lower() == 'ping'])

ipRegex = re.compile('^(((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])|((([0-9a-fA-F]){1,4})\\:){7}([0-9a-fA-F]){1,4})$') 

def formatUserInfo(title: str, username: str, content: str, additionalOptOut: list[str]=[]):
    optOutLists = ']] oder '.join([f'[[{liste}|dieser' for liste in additionalOptOut + ['Benutzer:DerIchBot/Opt-Out Liste']])
    return f"""
== {title} ==

Hallo{'' if re.match(ipRegex, username) else ' '+username},

{content}

Ich bin übrigens nur ein [[WP:Bots|Bot]]. Wenn ich nicht richtig funktioniere, sag bitte [[Benutzer Diskussion:DerIch27|DerIch27]] bescheid. Wenn du nicht mehr von mir benachrichtigt werden möchtest, kannst du dich auf {optOutLists} Liste]] eintragen.

Freundliche Grüsse  --~~~~"""