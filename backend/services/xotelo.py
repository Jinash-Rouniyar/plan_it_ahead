"""
Xotelo API integration for hotel/accommodation search and pricing
"""
import os
import requests
from typing import Optional, Dict, List, Any
from datetime import datetime

XOTELO_BASE_URL = 'https://data.xotelo.com/api'
DEFAULT_LOCATION_KEY = 'g294197'  # Default location key for testing


def search_hotels(location: str, check_in: str, check_out: str, guests: int = 2, 
                  min_price: Optional[float] = None, max_price: Optional[float] = None,
                  limit: int = 20) -> List[Dict[str, Any]]:
    """
    Search for hotels/accommodations using Xotelo API /list endpoint
    
    Args:
        location: Location name (will use default location_key for now)
        check_in: Check-in date (YYYY-MM-DD) - not used in /list endpoint
        check_out: Check-out date (YYYY-MM-DD) - not used in /list endpoint
        guests: Number of guests - not used in /list endpoint
        min_price: Minimum price per night - filter after fetching
        max_price: Maximum price per night - filter after fetching
        limit: Maximum number of results (default: 20, max: 100)
    
    Returns:
        List of hotel dictionaries
    """
    # Use /list endpoint with location_key
    url = f"{XOTELO_BASE_URL}/list"
    params = {
        'location_key': DEFAULT_LOCATION_KEY,
        'limit': min(limit, 100),  # Max 100
        'offset': 0,
        'sort': 'best_value'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Check for errors
        if data.get('error'):
            print(f"Xotelo API error: {data.get('error')}")
            return []
        
        # Extract hotel list from result
        result = data.get('result', {})
        hotels_list = result.get('list', [])
        
        # Format hotels to match expected structure
        formatted_hotels = []
        for hotel in hotels_list[:limit]:
            price_min = hotel.get('price_ranges', {}).get('minimum', 0)
            price_max = hotel.get('price_ranges', {}).get('maximum', 0)
            avg_price = (price_min + price_max) / 2 if price_min and price_max else 0
            
            # Apply price filters if specified
            if min_price and avg_price < min_price:
                continue
            if max_price and avg_price > max_price:
                continue
            
            formatted_hotel = {
                'hotel_id': hotel.get('key', ''),
                'hotel_key': hotel.get('key', ''),
                'name': hotel.get('name', 'Unknown'),
                'location': location,
                'rating': hotel.get('review_summary', {}).get('rating', 0),
                'review_count': hotel.get('review_summary', {}).get('count', 0),
                'price_per_night': avg_price,
                'price_min': price_min,
                'price_max': price_max,
                'image_url': hotel.get('image', ''),
                'url': hotel.get('url', ''),
                'accommodation_type': hotel.get('accommodation_type', 'Hotel'),
                'latitude': hotel.get('geo', {}).get('latitude'),
                'longitude': hotel.get('geo', {}).get('longitude'),
                'mentions': hotel.get('mentions', []),
                'check_in': check_in,
                'check_out': check_out,
                'guests': guests
            }
            formatted_hotels.append(formatted_hotel)
        
        return formatted_hotels
    except requests.exceptions.RequestException as e:
        print(f"Error fetching hotels from Xotelo: {e}")
        return []


def get_hotel_details(hotel_key: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a specific hotel
    Note: Xotelo doesn't have a direct details endpoint, so we search the list
    and return the matching hotel
    
    Args:
        hotel_key: Xotelo hotel key (e.g., 'g1234567-d12345678')
    
    Returns:
        Hotel details dictionary or None if not found
    """
    # Search in the list for this hotel
    hotels = search_hotels('', '', '', limit=100)
    for hotel in hotels:
        if hotel.get('hotel_key') == hotel_key:
            return hotel
    return None


def get_pricing(hotel_key: str, check_in: str, check_out: str, guests: int = 2, 
                rooms: int = 1, currency: str = 'USD') -> Optional[Dict[str, Any]]:
    """
    Get latest pricing information for a hotel using Xotelo /rates endpoint
    
    Args:
        hotel_key: Xotelo hotel key (e.g., 'g1234567-d12345678')
        check_in: Check-in date (YYYY-MM-DD)
        check_out: Check-out date (YYYY-MM-DD)
        guests: Number of adults (default: 2)
        rooms: Number of rooms (default: 1, max: 8)
        currency: Currency code (default: USD)
    
    Returns:
        Pricing information dictionary or None if not found
    """
    url = f"{XOTELO_BASE_URL}/rates"
    params = {
        'hotel_key': hotel_key,
        'chk_in': check_in,
        'chk_out': check_out,
        'adults': min(guests, 32),  # Max 32
        'rooms': min(rooms, 8),  # Max 8
        'currency': currency
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Check for errors
        if data.get('error'):
            print(f"Xotelo API error: {data.get('error')}")
            return None
        
        result = data.get('result', {})
        rates = result.get('rates', [])
        
        if not rates:
            return None
        
        # Find best rate (lowest price)
        best_rate = min(rates, key=lambda x: x.get('rate', float('inf')))
        
        return {
            'hotel_key': hotel_key,
            'check_in': check_in,
            'check_out': check_out,
            'guests': guests,
            'rooms': rooms,
            'currency': currency,
            'rates': rates,
            'best_rate': {
                'code': best_rate.get('code'),
                'name': best_rate.get('name'),
                'rate': best_rate.get('rate'),
                'rate_per_night': best_rate.get('rate')
            },
            'timestamp': data.get('timestamp')
        }
    except requests.exceptions.RequestException as e:
        print(f"Error fetching pricing from Xotelo: {e}")
        return None


def get_hotel_heatmap(hotel_key: str, check_out: str) -> Optional[Dict[str, Any]]:
    """
    Get hotel pricing heatmap for a specific hotel using Xotelo /heatmap endpoint
    
    Args:
        hotel_key: Xotelo hotel key (e.g., 'g1234567-d12345678')
        check_out: Check-out date (YYYY-MM-DD)
    
    Returns:
        Heatmap data dictionary or None if not found
    """
    url = f"{XOTELO_BASE_URL}/heatmap"
    params = {
        'hotel_key': hotel_key,
        'chk_out': check_out
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Check for errors
        if data.get('error'):
            print(f"Xotelo API error: {data.get('error')}")
            return None
        
        result = data.get('result', {})
        heatmap = result.get('heatmap', {})
        
        return {
            'hotel_key': hotel_key,
            'check_out': check_out,
            'heatmap': {
                'average_price_days': heatmap.get('average_price_days', []),
                'cheap_price_days': heatmap.get('cheap_price_days', []),
                'high_price_days': heatmap.get('high_price_days', [])
            },
            'timestamp': data.get('timestamp')
        }
    except requests.exceptions.RequestException as e:
        print(f"Error fetching heatmap from Xotelo: {e}")
        return None



