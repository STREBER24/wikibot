from datetime import datetime
import recentChanges
import speedcubing
import edelmetalle
import traceback
import logging
import optOut
import utils

if __name__ == '__main__':
    try:
        logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
        utils.sendTelegram('Start daily routine ...', silent=True)
        
        print('\n======== SPEEDCUBING ========')
        speedcubing.run()
    
        print('\n======== EDELMETALLE ========')
        edelmetalle.run()
    
        print('\n======== OPT-OUT ========')
        optOut.download()
        
        print('\n======== WARTUNGSLISTE ========')
        recentChanges.checkPagesInProblemList()
        
        print(f'\n[{datetime.now()}] finished daily routine\n')
    
    except Exception:
        print('[FAILED]')
        utils.sendTelegram(traceback.format_exc())
        
