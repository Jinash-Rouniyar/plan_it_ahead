"""
SerpAPI TripAdvisor search integration for attractions
"""
import os
import requests
from typing import List, Dict, Any, Optional

SERPAPI_API_KEY = os.getenv('SERP_API_KEY')
SERPAPI_BASE_URL = 'https://serpapi.com/search'


def search_tripadvisor(query: str, location: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
    """Search TripAdvisor via SerpAPI and return normalized attraction items.

    Returns a list of dicts with keys: name, description, lat, lon, image_url, type, rating
    """
    if not SERPAPI_API_KEY:
        return []

    # Use 'q' and 'ssrc' to match SerpAPI TripAdvisor examples
    params = {
        'engine': 'tripadvisor',
        'api_key': SERPAPI_API_KEY,
        'q': query,
        'ssrc': 'A',
        'num': limit,
        'hl': 'en'
    }
    if location:
        params['location'] = location

    try:
        resp = requests.get(SERPAPI_BASE_URL, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        # SerpAPI TripAdvisor responses include 'locations' key in product/attraction searches
        candidates = []
        if isinstance(data.get('locations'), list) and data.get('locations'):
            candidates = data.get('locations')
        else:
            # fall back to other keys
            for key in ('results', 'local_results', 'places', 'data', 'organic_results'):
                if key in data and isinstance(data[key], list) and data[key]:
                    candidates = data[key]
                    break

        results = []
        for item in candidates[:limit]:
            # Extract common TripAdvisor fields used by SerpAPI
            name = item.get('title') or item.get('name') or item.get('location_name') or ''
            description = item.get('description') or item.get('snippet') or item.get('subtitle') or ''
            rating = item.get('rating') or item.get('stars') or None
            reviews = item.get('reviews') or item.get('review_count') or item.get('num_reviews') or None
            location_id = item.get('location_id') or item.get('id') or None
            location_type = item.get('location_type') or item.get('type') or None
            link = item.get('link') or item.get('url') or None
            thumbnail = item.get('thumbnail') or (item.get('photo') and item.get('photo').get('thumbnail')) or None

            lat = None
            lon = None
            # Some TripAdvisor items include a nested 'coordinates' dict
            coords = item.get('coordinates') or item.get('location') or None
            if isinstance(coords, dict):
                lat = coords.get('lat')
                lon = coords.get('lon')

            # Price extraction - TripAdvisor product listings may include price fields
            price = None
            currency = None
            if 'price' in item and item.get('price'):
                price = item.get('price')
            elif 'starting_price' in item:
                price = item.get('starting_price')
            elif item.get('price_info') and isinstance(item.get('price_info'), dict):
                price = item['price_info'].get('amount')
                currency = item['price_info'].get('currency')

            results.append({
                'name': name,
                'description': description,
                'lat': lat,
                'lon': lon,
                'image_url': thumbnail,
                'type': location_type,
                'rate': rating,
                'reviews': reviews,
                'link': link,
                'location_id': location_id,
                'price': price,
                'currency': currency
            })

        return results
    except Exception:
        return []


def search_tripadvisor_hotels(query: str, location: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
    """Search TripAdvisor (hotels) via SerpAPI and return normalized hotel items.

    Returns a list of dicts with keys: name, description, lat, lon, image_url, rating, reviews, link, price
    """
    if not SERPAPI_API_KEY:
        return []

    params = {
        'engine': 'tripadvisor',
        'api_key': SERPAPI_API_KEY,
        'q': query,
        'ssrc': 'h',
        'num': limit,
        'hl': 'en'
    }
    if location:
        params['location'] = location

    try:
        resp = requests.get(SERPAPI_BASE_URL, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        candidates = []
        if isinstance(data.get('locations'), list) and data.get('locations'):
            candidates = data.get('locations')
        else:
            for key in ('results', 'local_results', 'places', 'data', 'organic_results'):
                if key in data and isinstance(data[key], list) and data[key]:
                    candidates = data[key]
                    break

        results = []
        for item in candidates[:limit]:
            name = item.get('title') or item.get('name') or ''
            description = item.get('description') or item.get('snippet') or ''
            rating = item.get('rating') or item.get('stars') or None
            reviews = item.get('reviews') or item.get('review_count') or None
            link = item.get('link') or item.get('url') or None
            thumbnail = item.get('thumbnail') or (item.get('photo') and item.get('photo').get('thumbnail')) or None

            # Extract a single numeric price per night when possible.
            price = None
            currency = None
            # Some SerpAPI items return price as a string like "$123" or as a nested dict
            raw_price = None
            if item.get('price'):
                raw_price = item.get('price')
            elif item.get('price_info') and isinstance(item.get('price_info'), dict):
                # price_info may contain amount and currency
                raw_price = item['price_info'].get('amount') or item['price_info'].get('price')
                currency = item['price_info'].get('currency')

            if raw_price:
                # Normalize strings like "$123" or "USD 123" to numeric amount (assume per-night)
                try:
                    if isinstance(raw_price, (int, float)):
                        price = float(raw_price)
                    else:
                        # remove currency symbols and non-number characters except dot and comma
                        s = str(raw_price)
                        s = s.replace(',', '')
                        # extract first occurrence of number
                        import re
                        m = re.search(r"[0-9]+(?:\.[0-9]+)?", s)
                        if m:
                            price = float(m.group(0))
                except Exception:
                    price = None

            lat = None
            lon = None
            coords = item.get('coordinates') or item.get('location') or None
            if isinstance(coords, dict):
                lat = coords.get('lat')
                lon = coords.get('lon')

            # Create a normalized hotel object with a single price_per_night numeric field
            results.append({
                'name': name,
                'description': description,
                'lat': lat,
                'lon': lon,
                'image_url': thumbnail,
                'rating': rating,
                'reviews': reviews,
                'link': link,
                'price_per_night': price,
                'currency': currency,
                'hotel_key': item.get('location_id') or item.get('id') or item.get('hotel_id')
            })

        return results
    except Exception:
        return []
