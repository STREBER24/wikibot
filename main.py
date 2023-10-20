import speedcubing
import edelmetalle

if __name__ == '__main__':
    changes = []
    
    print('\n======== SPEEDCUBING ========')
    changes.append(speedcubing.run())
    
    print('\n======== EDELMETALLE ========')
    changes.append(edelmetalle.run())
    
    if True in changes: input('Press enter to exit ...')
