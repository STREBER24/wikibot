from pywikibot import pagegenerators as pg
import wikitextparser as wtp
import pywikibot
import bs4

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
