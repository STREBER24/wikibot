import pywikibot
import requests
import typing
import utils
import json
import bs4
import io
import re

disciplines = {'2x2x2': '2x2x2 Cube', 
               '3x3x3': '3x3x3 Cube', 
               '3x3x3blind': '3x3x3 Blindfolded', 
               '3x3x3onehanded': '3x3x3 One-Handed', 
               '3x3x3withfeet': '3x3x3 With Feet', 
               '3x3x3multiblind': '3x3x3 Multi-Blind', 
               '3x3x3fewestmoves': '3x3x3 Fewest Moves', 
               '4x4x4': '4x4x4 Cube', 
               '4x4x4blind': '4x4x4 Blindfolded', 
               '5x5x5': '5x5x5 Cube', 
               '5x5x5blind': '5x5x5 Blindfolded', 
               '6x6x6': '6x6x6 Cube', 
               '7x7x7': '7x7x7 Cube', 
               'Pyraminx': 'Pyraminx', 
               'Megaminx': 'Megaminx', 
               'Skewb': 'Skewb', 
               'Square1': 'Square-1', 
               'Clock': 'Clock'}

def differentLinks(name: str):
    links = dict()
    if links.get(name) != None:
        return links.get(name)
    if re.search(' \(.+\)$', name):
        return re.sub(' \(.+\)$', '', name)

def editWiki(data: dict[str, tuple[list[dict[str, str]], list[dict[str, str]]]], 
             parser: typing.Callable[[list[dict[str, str]], str], str], 
             changedDisciplines: list[str], 
             pagename: str, 
             forcedSummary: str|None = None):
    site = pywikibot.Site('de', 'wikipedia')
    page = pywikibot.Page(site, pagename)
    if page.latest_revision["user"] == 'DerIchBot' or input(f'{page.latest_revision["user"]} hat die Seite {pagename} zuletzt geändert. Trotzdem fortfahren? ').strip().lower() in ['y', 'j', 'ja', 'yes']:
        newText = generatePage(data, parser)
        if newText != page.text:
            print('Update page ...')
            page.text = newText
            summary = f'Bot: Aktualisiere Rekord{"e" if len(changedDisciplines)>1 else ""} für {" und ".join(changedDisciplines)}.'
            site.login()
            assert site.logged_in()
            page.save(botflag=True, minor=False, summary=(summary if forcedSummary==None else f'Bot: {forcedSummary}'))
            site.logout()
        else:
            print('Page content did not change.')
    else:
        print('skipped')

def generatePage(data: dict[str, tuple[list[dict[str, str]], list[dict[str, str]]]], parser: typing.Callable[[list[dict[str, str]], str], str]):
    return '<onlyinclude><includeonly><!--\n-->{{#switch: {{{2}}}<!--\n  -->| Single = {{#switch: {{{1}}}' + ''.join(['<!--\n    -->| '+i.ljust(16)+' = '+parser(data.get(disciplines.get(i))[0], i) for i in disciplines.keys()]) + '<!--\n    -->| #default         = ' + parseError('Parameter 1 ungültig!') + ' }}<!--\n  -->| Average = {{#switch: {{{1}}}' + ''.join(['<!--\n    -->| '+i.ljust(16)+' = '+parser(data.get(disciplines.get(i))[1], i) for i in disciplines.keys()]) + '<!--\n    -->| #default         = ' + parseError('Parameter 1 ungültig!') + ' }}<!--\n  -->| #default = ' + parseError('Parameter 2 ungültig!') + '<!--\n-->}}</includeonly></onlyinclude>\n\n{{Dokumentation}}'

def parseSwitch(data: list[str], key: int):
    data = (['', '', '', ''] + data)[-4:]
    return '{{#switch: {{{' + str(key) + '}}} |4=' + data[0] + ' |3='+ data[1] + ' |2='+ data[2] + ' |#default=' + data[3] + '}}'

def parseDates(data: list[dict[str, str]], discipline: str):
    if data == []: return parseError('Keine Daten für diese Parameterkombination.')
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    dates = [i.get('date') for i in data]
    dates = [utils.formatDate(i[4:6], months.index(i[0:3])+1, i[8:12]) for i in dates]
    return parseSwitch(dates, 3)

def parseNames(data: list[dict[str, str]], discipline: str):
    if data == []: return parseError('Keine Daten für diese Parameterkombination.')
    months = {'Jan': 'Januar', 'Feb': 'Februar', 'Mar': 'März', 'Apr': 'April', 'May': 'Mai', 'Jun': 'Juni',
              'Jul': 'Juli', 'Aug': 'August', 'Sep': 'September', 'Oct': 'Oktober', 'Nov': 'November', 'Dec': 'Dezember'}
    names = [i.get('name') for i in data]
    links = ['[[' + (i if differentLinks(i)==None else differentLinks(i)+'|'+i) + ']]' for i in names]
    return '{{#if: {{#invoke:TemplUtl|faculty|{{{3|}}}}} |<!--\n      -->' + parseSwitch(links, 4) + '|<!--\n      -->' + parseSwitch(names, 4) + '}}'

def parseTime(data: list[dict[str, str]], discipline: str):
    if data == []: return parseError('Keine Daten für diese Parameterkombination.')
    ergebnis = data[0].get('single') if data[0].get('single') != '' else data[0].get('average')
    assert ergebnis != '' and ergebnis != None
    einheit = 'Züge' if 'moves' in discipline else ('Minuten' if ':' in ergebnis else 'Sekunden')
    ergebnis = ergebnis.replace('.',',').split(' ')
    return ergebnis[0] + '<!--' + ' '*(8-len(ergebnis[0])) + '-->{{#if: {{#invoke:TemplUtl|faculty|{{{3|}}}}} | ' + ('&#32;in '+ergebnis[1] if len(ergebnis)>1 else '') + '&nbsp;' + einheit + '}}'

def parseEvents(data: list[dict[str, str]], discipline: str):
    if data == []: return parseError('Keine Daten für diese Parameterkombination.')
    events = [i.get('competition') for i in data]
    return parseSwitch(events, 3)

def parseError(text: str):
    return f'<span class="error">{text}</span> [[Kategorie:Wikipedia:Vorlagenfehler/Speedcubing]]'

def stripTag(tag: bs4.element.Tag | None):
    if tag == None:
        return ''
    return tag.text.strip()

def scrape():
    print('Lade worldcubeassociation.org ...')
    result = requests.get('https://www.worldcubeassociation.org/results/records?show=history')
    assert result.ok
    soup = bs4.BeautifulSoup(result.text, 'html.parser')
    body = soup.find(id='results-list')
    titles = body.find_all('h2')
    tables = body.find_all('div', {'class': 'table-responsive'})
    assert len(titles) == len(tables)
    data: dict[str, tuple[list[dict[str, str]], list[dict[str, str]]]] = dict()
    for title, table in zip(titles, tables):
        title: bs4.element.Tag
        table: bs4.element.Tag
        tbody = table.find('tbody')
        assert tbody != None
        results: list[dict[str, str]] = [{'date': stripTag(line.find('td', {'class': 'date'})),
                                          'single': stripTag(line.find('td', {'class': 'single'})),
                                          'average': stripTag(line.find('td', {'class': 'average'})),
                                          'name': stripTag(line.find('td', {'class': 'name'})),
                                          'competition': stripTag(line.find('td', {'class': 'competition'}))
                                          } for line in tbody.find_all('tr')]
        single: list[dict[str, str]] = []
        average: list[dict[str, str]] = []
        for res in results:
            if (res.get('single') != '') and ((single == []) or single[0].get('single') == res.get('single')):
                single.append(res)
            if (res.get('average') != '') and ((average == []) or average[0].get('average') == res.get('average')):
                average.append(res)
        data[title.text.strip()] = (single, average)
    return data
    
def run():
    newData = scrape()
    with io.open('speedcubing-data.json', 'r', encoding='utf8') as file:
        oldData: dict[str, tuple] = json.loads(file.read())
    with io.open('speedcubing-data.json', 'w', encoding='utf8') as file:
        json.dump(newData, file, indent=2, ensure_ascii=False)
    changedDisciplines = [i for i in disciplines.keys() if json.dumps(oldData.get(disciplines.get(i)), ensure_ascii=False) != json.dumps(newData.get(disciplines.get(i)), ensure_ascii=False)]
    changes = changedDisciplines != []
    if not changes:
        print('Keine Änderung an den Rohdaten.')
    else:
        editWiki(newData, parseDates,  changedDisciplines, 'Vorlage:Speedcubing-Rekorddatum')
        editWiki(newData, parseTime,   changedDisciplines, 'Vorlage:Speedcubing-Rekordzeit')
        editWiki(newData, parseEvents, changedDisciplines, 'Vorlage:Speedcubing-Rekordevent')
        editWiki(newData, parseNames,  changedDisciplines, 'Vorlage:Speedcubing-Rekordhalter')
    print('Erfolgreich ausgeführt.')
    return changes
    
if __name__ == '__main__':
    # editWiki(newData, parseEvents, changedDisciplines, 'Benutzer:DerIchBot/Spielwiese/Vorlage:Speedcubing-Rekorddatum', forcedSummary='Tests ...')
    # print(generatePage(newData, parseNames))
    run()
