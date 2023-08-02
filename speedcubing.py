
import wikitextparser as wtp
import pywikibot
import requests
import typing
import json
import bs4
import io

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

differentLinks = {'Yiheng Wang (王艺衡)': 'Yiheng Wang',
                  'Guanbo Wang (王冠博)': 'Guanbo Wang',
                  'Lim Hung (林弘)': 'Lim Hung',
                  'Yuxuan Wang (王宇轩)': 'Yuxuan Wang'}

def editWiki(data: dict[str, tuple[list[dict[str, str]], list[dict[str, str]]]], 
             parser: typing.Callable[[list[dict[str, str]], str], str], 
             changedDisciplines: list[str], 
             pagename: str, 
             forcedSummary: str|None = None):
    site = pywikibot.Site('de', 'wikipedia')
    page = pywikibot.Page(site, pagename)
    lastEdit = [cell.plain_text().strip('| \n') for cell in wtp.parse(page.getVersionHistoryTable(total=1)).tables[0].cells(row=1)]
    if lastEdit[2] == 'DerIchBot' or input(f'{lastEdit[2]} hat die Seite {pagename} zuletzt geändert. Trotzdem fortfahren? ').strip().lower() in ['y', 'j', 'ja', 'yes']:
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

def parseDates(data: list[dict[str, str]], discipline: str):
    if data == []: return parseError('Keine Daten für diese Parameterkombination.')
    months = {'Jan': 'Januar', 'Feb': 'Februar', 'Mar': 'März', 'Apr': 'April', 'May': 'Mai', 'Jun': 'Juni',
              'Jul': 'Juli', 'Aug': 'August', 'Sep': 'September', 'Oct': 'Oktober', 'Nov': 'November', 'Dec': 'Dezember'}
    dates = [i.get('date') for i in data]
    dates = (['', '', '', ''] + [f'{i[4:6]}. {months.get(i[0:3])} {i[8:12]}' for i in dates])[-4:]
    return '{{#switch: {{{3}}} |4=' + dates[0] + ' |3='+ dates[1] + ' |2='+ dates[2] + ' |#default=' + dates[3] + '}}'

def parseTime(data: list[dict[str, str]], discipline: str):
    if data == []: return parseError('Keine Daten für diese Parameterkombination.')
    ergebnis = data[0].get('single') if data[0].get('single') != '' else data[0].get('average')
    assert ergebnis != '' and ergebnis != None
    einheit = 'Züge' if 'moves' in discipline else ('Minuten' if ':' in ergebnis else 'Sekunden')
    ergebnis = ergebnis.replace('.',',').split(' ')
    return ergebnis[0] + '<!--' + ' '*(8-len(ergebnis[0])) + '-->{{#if: {{#invoke:TemplUtl|faculty|{{{3|}}}}} | ' + ('&#32;in '+ergebnis[1] if len(ergebnis)>1 else '') + '&nbsp;' + einheit + '}}'

def parseError(text: str):
    return f'<span class="error">{text}</span> [[Kategorie:Wikipedia:Vorlagenfehler/Speedcubing]]'

def stripTag(tag: bs4.element.Tag | None):
    if tag == None:
        return ''
    return tag.text.strip()

def scrape():
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
        
if __name__ == '__main__':
    newData = scrape()
    with io.open('speedcubing-data.json', 'r', encoding='utf8') as file:
        oldData: dict[str, tuple] = json.loads(file.read())
    with io.open('speedcubing-data.json', 'w', encoding='utf8') as file:
        json.dump(newData, file, indent=2, ensure_ascii=False)
    changedDisciplines = [i for i in disciplines.keys() if json.dumps(oldData.get(disciplines.get(i)), ensure_ascii=False) != json.dumps(newData.get(disciplines.get(i)), ensure_ascii=False)]
    if changedDisciplines == []:
        print('Keine Änderung an den Rohdaten.')
    else:
        # editWiki(newData, parseDates, changedDisciplines, 'Vorlage:Speedcubing-Rekorddatum')
        # editWiki(newData, parseTime,  changedDisciplines, 'Vorlage:Speedcubing-Rekordzeit')
        pass
    editWiki(newData, parseTime, changedDisciplines, 'Benutzer:DerIchBot/Spielwiese/Vorlage:Speedcubing-Rekorddatum', forcedSummary='Tests ...')
    print(generatePage(newData, parseTime))
