import citeParamChecker
import pywikibot
import unittest
import utils
import bs4


class TestDateParsing(unittest.TestCase):
    def test_dates(self):
        site = pywikibot.Site('de', 'wikipedia')
        page = pywikibot.Page(site, 'Benutzer:DerIchBot/Datumstests')
        rawDates = [i.split('|')[2] for i in page.get().split('\n\n')]
        parsedDates = [p.text.replace(u'\xa0', u' ').strip() for p in bs4.BeautifulSoup(page.get_parsed_page(), 'html.parser').find_all('p')]
        self.assertEqual(len(rawDates), len(parsedDates))
        for raw, parsed in zip(rawDates, parsedDates):
            with self.subTest(raw=raw, parsed=parsed):
                timestamp = citeParamChecker.parseWeirdDateFormats(raw)
                if timestamp != False: timestamp = utils.formatDateFromDatestring(timestamp)
                if timestamp == False: timestamp = 'Format invalid'
                self.assertEqual(timestamp, parsed)


if __name__ == '__main__':
    unittest.main()