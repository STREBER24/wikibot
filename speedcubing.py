import requests
import json
import bs4
import io

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
    data: dict[str, tuple[list[dict], list[dict]]] = dict()
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
    data = scrape()
    with io.open('test.json', 'w', encoding='utf8') as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
