import os
import json
import logging
from typing import Dict

from dotenv import load_dotenv
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def hent_kjoretoydata(kjennemerke: str) -> Dict:
    """Hent kjøretøydata fra Statens Vegvesen basert på kjennemerke."""
    load_dotenv()

    api_key = os.getenv('SVV_API_KEY')
    
    if not api_key:
        raise EnvironmentError('Missing SVV_API_KEY in environment configuration')

    api_url = 'https://akfell-datautlevering.atlas.vegvesen.no/enkeltoppslag/kjoretoydata'
    logger.info("Calling vehicle API %s with kjennemerke=%s", api_url, kjennemerke)

    headers = {
        'SVV-Authorization': f'Apikey {api_key}',
        'Content-Type': 'application/json'
    }

    api_response = requests.get(
        api_url,
        params={'kjennemerke': kjennemerke},
        headers=headers
    )
    
    try:
        api_response.raise_for_status()
        logger.info("Successfully retrieved vehicle data")
        return api_response.json()
    except requests.HTTPError:
        logger.error("Vehicle API request failed: %s", api_response.text)
        raise 