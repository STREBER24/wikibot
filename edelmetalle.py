import wikitextparser as wtp
import pywikibot
import requests
import utils
import time

def fetch(metall: str):
    print(f'fetch {metall} ...')
    res = requests.get(f'https://prices.lbma.org.uk/json/{metall}.json')
    data = res.json()
    return data[-1]['d'], data[-1]['v'][0]

def fetchGoldSilver():
    silber = fetch('silver')
    gold = fetch('gold_pm')
    assert silber[0] == gold[0]
    datum = utils.formatDate(silber[0][8:10], silber[0][5:7], silber[0][0:4])
    return datum, str(gold[1]), str(silber[1])

def run():
    site = pywikibot.Site('de', 'wikipedia')
    page = pywikibot.Page(site, 'Vorlage:Goldpreis')
    daysSinceLastRevistion = (time.time() - page.latest_revision['timestamp'].timestamp())/60/60/24
    if daysSinceLastRevistion < 7:
        print('skip update')
        return False
    if not(page.latest_revision['user'] == 'DerIchBot' or input(f'{page.latest_revision["user"]} hat die Seite Vorlage:Goldpreis zuletzt geändert. Trotzdem fortfahren? ').strip().lower() in ['y', 'j', 'ja', 'yes']):
        return False
    noinclude = wtp.parse(page.text).get_tags()[1]
    assert noinclude.name == 'noinclude'
    datum, gold, silber = fetchGoldSilver()
    page.text = "<includeonly>{{#if:{{{Datum|}}} | " + datum + " | {{#if:{{{AG|}}}\n| {{formatnum:\n     {{#expr: ( " + silber + " <!-- Silber in USD --> / {{Wechselkursdaten|USD}} * {{Wechselkursdaten|{{{1|USD}}}}} / {{#if:{{{Gramm|}}}|31.1034768|1}} ) ^ {{#if:{{{Invert|}}}|-1|1}} * {{{Faktor|1}}} round {{{NKS|2}}} }}\n  }}\n| {{formatnum:\n     {{#expr: ( " + gold + " <!-- Gold in USD --> / {{Wechselkursdaten|USD}} * {{Wechselkursdaten|{{{1|USD}}}}} / {{#if:{{{Gramm|}}}|31.1034768|1}} ) ^ {{#if:{{{Invert|}}}|-1|1}} * {{{Faktor|1}}} round {{{NKS|2}}} }}\n  }}\n}}\n}}</includeonly>" + str(noinclude)
    site.login()
    assert site.logged_in()
    page.save(botflag=True, minor=False, summary=(f'Bot: Aktualisiere Preise: Schlusskurs vom {datum}'))
    site.logout()
    return True

if __name__ == '__main__':
    run()
