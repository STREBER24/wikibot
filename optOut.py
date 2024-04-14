import wikitextparser as wtp
import pywikibot
import utils
import re

def download():
    site = pywikibot.Site('de', 'wikipedia')
    page = pywikibot.Page(site, 'Benutzer:DerIchBot/Opt-Out Liste')
    content = page.get()
    parsed = wtp.parse(content)
    pages = [link.target for link in parsed.wikilinks]
    utils.dumpJson('data/opt-out.json', pages)

def downloadXqBotList():
    site = pywikibot.Site('de', 'wikipedia')
    page = pywikibot.Page(site, 'Benutzer:Xqbot/Opt-out:LD-Hinweis')
    content = page.get()
    parsed = wtp.parse(content)
    user = list(set([':'.join(link.target.split(':')[1:]) for link in parsed.wikilinks if re.match('^(Benutzer:|Benutzer Diskussion:)', link.target)]))
    utils.dumpJson('data/opt-out-ld.json', user)

def isAllowed(page: pywikibot.Page):
    optOutList: list[str] = utils.loadJson('data/opt-out.json', [])
    if page.title() in optOutList: return False
    parsed = wtp.parse(page.text)
    for template in parsed.templates:
        if template.name.strip() == 'nobots':
            arg = utils.findTemplateArg(template,'1')
            if arg is None: return False
            if arg == 'all': return False
            if 'DerIchBot' in arg.split(','): return False
        elif template.name.strip() == 'bots':
            arg = utils.findTemplateArg(template,'deny')
            if arg is None: continue
            if arg == 'all': return False
            if 'DerIchBot' in arg.split(','): return False
    return True    

if __name__ == '__main__':
    download()
    downloadXqBotList()