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

def includes(pagename: str):
    optOutList: list[str] = utils.loadJson('data/opt-out.json', [])
    return pagename in optOutList

if __name__ == '__main__':
    download()
    downloadXqBotList()