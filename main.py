import speedcubing
import edelmetalle

if __name__ == '__main__':
    changes = []
    try:
        
        print('\n======== SPEEDCUBING ========')
        changes.append(speedcubing.run())
    
        print('\n======== EDELMETALLE ========')
        changes.append(edelmetalle.run())
    
        if True in changes: input('\nPress enter to exit ...')
    
    except Exception as e:
        print(f'[FAILED] {e}')
        input('\nPress enter to exit ...')
