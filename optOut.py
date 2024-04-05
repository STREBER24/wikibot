import wikitextparser as wtp
import pywikibot
import utils

def download():
    site = pywikibot.Site('de', 'wikipedia')
    page = pywikibot.Page(site, 'Benutzer:DerIchBot/Opt-Out Liste')
    content = page.get()
    parsed = wtp.parse(content)
    pages = [link.target for link in parsed.wikilinks]
    utils.dumpJson('data/opt-out.json', pages)

def includes(pagename: str):
    optOutList: list[str] = utils.loadJson('data/opt-out.json', [])
    return pagename in optOutList

if __name__ == '__main__':
    download()