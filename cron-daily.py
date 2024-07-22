from datetime import datetime
import citeParamChecker
import speedcubing
import edelmetalle
import pywikibot
import telegram
import logging
import optOut
import os

if __name__ == '__main__':
    try:
        logging.basicConfig(format='%(asctime)s - %(levelname)s - DAILY - %(message)s', level=logging.INFO)
        
        if os.system('systemctl is-active --quiet recent-changes') != 0:
            telegram.send('WARNING: recent changes service is not running')
        
        site = pywikibot.Site('de', 'wikipedia')
        
        print('\n======== SPEEDCUBING ========')
        speedcubing.run()
    
        print('\n======== EDELMETALLE ========')
        edelmetalle.run()
    
        print('\n======== OPT-OUT ========')
        optOut.downloadAll()
        
        print('\n======== WARTUNGSLISTE ========')
        citeParamChecker.checkPagesInProblemList(site)
        
        print('\n======== DATUMSFEHLER BENACHRICHTIGUNGEN ========')
        citeParamChecker.sendPlannedNotifications(site)
        
        print(f'\n[{datetime.now()}] finished daily routine\n')
        telegram.send('Finished daily routine successfully ...', silent=True)
    
    except Exception:
        print('[FAILED]')
        telegram.handleException()
        
