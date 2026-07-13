#!/usr/bin/env python
import logging
import sys
import os

# Agregamos src al path
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))

from src.modules.meta_ads.browser.browser_manager import BrowserManager
from src.modules.meta_ads.browser.session_manager import SessionManager
from src.modules.meta_ads.acquisition.ads_searcher import AdsSearcher
from src.modules.meta_ads.acquisition.ads_extractor import AdsExtractor

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s' # Formato limpio para igualar la salida esperada por el usuario
)
logger = logging.getLogger(__name__)

def run_poc():
    # Usamos headless=True por defecto
    with BrowserManager(headless=True) as browser:
        session_manager = SessionManager(browser)
        page = session_manager.create_session()
        
        searcher = AdsSearcher(page)
        extractor = AdsExtractor(page)
        
        keyword = "curso"
        
        try:
            searcher.search(keyword)
            ad = extractor.extract_first_ad()
            
            if ad:
                logger.info(f"\nDTO Extraído:\n{ad}")
            else:
                logger.warning("No se extrajo ningún anuncio.")
                
        finally:
            session_manager.close_session()

    logger.info("Proceso finalizado.")

if __name__ == "__main__":
    run_poc()
