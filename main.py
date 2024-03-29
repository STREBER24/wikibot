import speedcubing
import edelmetalle
import traceback
import utils

if __name__ == '__main__':
    changes = []
    try:
        utils.sendTelegram('Start main routine ...', silent=True)
        
        print('\n======== SPEEDCUBING ========')
        changes.append(speedcubing.run())
    
        print('\n======== EDELMETALLE ========')
        changes.append(edelmetalle.run())
        
        if True in changes: input('\nPress enter to exit ...')
    
    except Exception:
        print('[FAILED]')
        utils.sendTelegram(traceback.format_exc())
        traceback.print_exc()
        input('\nPress enter to exit ...')
