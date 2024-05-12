import traceback
import logging
import katdisk
import utils

if __name__ == '__main__':
    try:
        logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
        logging.info(f'start hourly routine')
        
        katdisk.handleKatDiscussionToday()
        
        logging.info(f'finished hourly routine')
    
    except Exception:
        logging.error(traceback.format_exc())
        utils.sendTelegram(traceback.format_exc())
        
