import os
import requests
from typing import Optional

SERPAPI_API_KEY = os.getenv('SERP_API_KEY')
SERPAPI_BASE_URL = 'https://serpapi.com/search'


def search_image(query: str, destination: str = '') -> Optional[str]:
    if not SERPAPI_API_KEY:
        return None
    
    search_query = f"{query} {destination}".strip()
    
    try:
        response = requests.get(
            SERPAPI_BASE_URL,
            params={
                'api_key': SERPAPI_API_KEY,
                'engine': 'google_images',
                'q': search_query,
                'num': 3,
                'safe': 'active'
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            images = data.get('images_results', [])
            if images and len(images) > 0:
                for image in images:
                    image_url = image.get('thumbnail') or image.get('original') or image.get('link')
                    if image_url and image_url.startswith('http'):
                        return image_url
        return None
    except Exception:
        return None


def get_images_for_recommendations(recommendations: list, destination: str) -> list:
    for rec in recommendations:
        name = rec.get('name', '')
        if name:
            image_url = search_image(name, destination)
            if image_url:
                rec['image_url'] = image_url
    return recommendations

