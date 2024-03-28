import speedcubing
import edelmetalle
import traceback

if __name__ == '__main__':
    changes = []
    try:
        
        print('\n======== SPEEDCUBING ========')
        changes.append(speedcubing.run())
    
        print('\n======== EDELMETALLE ========')
        changes.append(edelmetalle.run())
    
        if True in changes: input('\nPress enter to exit ...')
    
    except Exception:
        print('[FAILED]')
        traceback.print_exc()
        input('\nPress enter to exit ...')
