from pywikibot.comms import eventstreams
import citeParamChecker
import deletionInfo
import pywikibot
import telegram
import logging
import katdisk
import utils
import time
import re

DELAY_THRESHOLD = 300 # 5min
class LagMonitor:
    def __init__(self):
        self.lastLagNotification: float = 0
        self.numberOfDelayedChanges = 0
        self.maxLag = 0
        self.minLag = 9999999999999999
        self.firstLag: float = 0
    def formatSeconds(self, timediff: int):
        result = f'{timediff%60} s'; timediff = timediff // 60
        if timediff == 0: return result
        result = f'{timediff%60} min, {result}'; timediff = timediff // 60
        if timediff == 0: return result
        result = f'{timediff%24} h, {result}'; timediff = timediff // 24
        if timediff == 0: return result
        return f'{timediff} d, {result}'
    def checkRevision(self, change: dict):
        lag = int(time.time() - change['timestamp'])
        if lag > DELAY_THRESHOLD and self.maxLag <= DELAY_THRESHOLD: self.firstLag = time.time()
        if lag > self.maxLag: self.maxLag = lag
        if lag < self.minLag: self.minLag = lag
        if lag > DELAY_THRESHOLD:
            logging.warning(f'Handled revision {change.get('revision')} with delay of {lag}s')
            self.numberOfDelayedChanges += 1
        if (self.maxLag > DELAY_THRESHOLD) and (time.time() - self.lastLagNotification > 600) and (time.time() - self.firstLag > 300):
            telegram.send(f'LAG WARNING\nminimum: {self.formatSeconds(self.minLag)}\nmaximum: {self.formatSeconds(self.maxLag)}\n{self.numberOfDelayedChanges} delayed changes', silent=True)
            self.numberOfDelayedChanges = 0
            self.lastLagNotification = time.time()
            self.maxLag = 0
            self.minLag = 9999999999999999

def monitorRecentChanges():
    allProblems = citeParamChecker.loadAllProblems()
    site = pywikibot.Site('de', 'wikipedia')
    stream = eventstreams.EventStreams(streams='recentchange')
    site.login()
    stream.register_filter(type='edit', wiki='dewiki')
    numberOfChanges = 0
    numberOfProblemsBefore = len(allProblems)
    lagMonitor = LagMonitor()
    while True:
        try:
            change = next(stream)
            logging.debug(f'handle recent change {change.get('revision')} on {change.get('title')}')
            lagMonitor.checkRevision(change)
            telegram.alarmOnChange(change)
            if change['namespace'] == 4: # Wikipedia:XYZ
                if re.match('^Wikipedia:Löschkandidaten/.', change['title']):
                    deletionInfo.handleDeletionDiscussionUpdate(site, change['title'], change)
                if re.match('^Wikipedia:WikiProjekt Kategorien/Diskussionen/[0-9]{4}/(Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)/[0-9][0-9]?$', change['title']):
                    katdisk.handleKatDiscussionUpdate(site, change['title'])
            elif change['namespace'] == 0: # Artikelnamensraum
                if len(allProblems) >= 300:
                    if utils.checkLastUpdate('check-problems-list-full', 90):
                        citeParamChecker.checkPagesInProblemList()
                        allProblems = citeParamChecker.loadAllProblems()
                else:
                    numberOfChanges += 1
                    allProblems = citeParamChecker.loadAllProblems()
                    allProblems += citeParamChecker.checkPage(site, change['title'], allProblems)
                    citeParamChecker.dumpAllProblems(allProblems)
                    if numberOfChanges >= 100:
                        logging.info(f'Checked 100 changes and found {len(allProblems)-numberOfProblemsBefore} problems.')
                        numberOfProblemsBefore = len(allProblems)
                        numberOfChanges = 0
        except Exception as e:
            e.add_note(f'failed while handling recent change {change.get('revision')} on {change.get('title')}')
            raise e

if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(levelname)s - RECENT CHANGES - %(message)s', level=logging.INFO)
    telegram.send('start recent changes service ...', silent=True)
    try:
        monitorRecentChanges()
    except KeyboardInterrupt:
        print('Exception: KeyboardInterrupt')
    except Exception as e:
        telegram.handleException()
            