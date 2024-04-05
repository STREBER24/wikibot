from datetime import datetime
import speedcubing
import edelmetalle
import traceback
import optOut
import utils

if __name__ == '__main__':
    try:
        utils.sendTelegram('Start daily routine ...', silent=True)
        
        print('\n======== SPEEDCUBING ========')
        speedcubing.run()
    
        print('\n======== EDELMETALLE ========')
        edelmetalle.run()
    
        print('\n======== OPT-OUT ========')
        optOut.download()
        
        print(f'\n[{datetime.now()}] finished daily routine\n')
    
    except Exception:
        print('[FAILED]')
        utils.sendTelegram(traceback.format_exc())
        
