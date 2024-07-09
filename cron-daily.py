from datetime import datetime
import citeParamChecker
import speedcubing
import edelmetalle
import telegram
import logging
import optOut

if __name__ == '__main__':
    try:
        logging.basicConfig(format='%(asctime)s - %(levelname)s - DAILY - %(message)s', level=logging.INFO)
        telegram.send('Start daily routine ...', silent=True)
        
        print('\n======== SPEEDCUBING ========')
        speedcubing.run()
    
        print('\n======== EDELMETALLE ========')
        edelmetalle.run()
    
        print('\n======== OPT-OUT ========')
        optOut.downloadAll()
        
        print('\n======== WARTUNGSLISTE ========')
        citeParamChecker.checkPagesInProblemList()
        
        print(f'\n[{datetime.now()}] finished daily routine\n')
    
    except Exception:
        print('[FAILED]')
        telegram.handleException()
        
