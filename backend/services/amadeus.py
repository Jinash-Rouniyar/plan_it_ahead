"""
Amadeus API integration for flight search and flight status
"""
import os
import requests
from typing import Optional, Dict, List, Any
from datetime import datetime

AMADEUS_API_KEY = os.getenv('AMADEUS_API_KEY')
AMADEUS_API_SECRET = os.getenv('AMADEUS_API_SECRET')
_base_url = os.getenv('AMADEUS_BASE_URL', 'https://test.api.amadeus.com')
if not _base_url.startswith(('http://', 'https://')):
    _base_url = f'https://{_base_url}'
AMADEUS_BASE_URL = _base_url.rstrip('/')
AMADEUS_TOKEN_URL = f"{AMADEUS_BASE_URL}/v1/security/oauth2/token"

# Cache for access token
_access_token = None
_token_expires_at = None


def _get_access_token() -> Optional[str]:
    """
    Get Amadeus API access token using client credentials
    """
    global _access_token, _token_expires_at
    
    # Check if we have a valid cached token
    if _access_token and _token_expires_at and datetime.now().timestamp() < _token_expires_at:
        return _access_token
    
    if not AMADEUS_API_KEY or not AMADEUS_API_SECRET:
        raise ValueError("AMADEUS_API_KEY and AMADEUS_API_SECRET must be set in environment variables")
    
    try:
        response = requests.post(
            AMADEUS_TOKEN_URL,
            data={
                'grant_type': 'client_credentials',
                'client_id': AMADEUS_API_KEY,
                'client_secret': AMADEUS_API_SECRET
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        _access_token = data.get('access_token')
        expires_in = data.get('expires_in', 1800)  # Default 30 minutes
        _token_expires_at = datetime.now().timestamp() + expires_in - 60  # Refresh 1 min early
        
        return _access_token
    except requests.exceptions.RequestException as e:
        print(f"Error getting Amadeus access token: {e}")
        return None


def search_flights(origin: str, destination: str, departure_date: str, 
                  return_date: Optional[str] = None, passengers: int = 1,
                  cabin_class: str = 'ECONOMY') -> List[Dict[str, Any]]:
    """
    Search for flights using Amadeus Flight Offers Search API
    
    Args:
        origin: Origin airport code (IATA) or city code
        destination: Destination airport code (IATA) or city code
        departure_date: Departure date (YYYY-MM-DD)
        return_date: Optional return date (YYYY-MM-DD) for round trips
        passengers: Number of passengers (default: 1)
        cabin_class: Cabin class ('ECONOMY', 'PREMIUM_ECONOMY', 'BUSINESS', 'FIRST')
    
    Returns:
        List of flight dictionaries
    """
    token = _get_access_token()
    if not token:
        raise ValueError("Failed to obtain Amadeus access token")
    
    url = f"{AMADEUS_BASE_URL}/v2/shopping/flight-offers"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    params = {
        'originLocationCode': origin.upper(),
        'destinationLocationCode': destination.upper(),
        'departureDate': departure_date,
        'adults': passengers,
        'max': 20
    }
    
    if return_date:
        params['returnDate'] = return_date
    
    # Map cabin class - Amadeus uses travelClass parameter
    cabin_class_map = {
        'economy': 'ECONOMY',
        'premium': 'PREMIUM_ECONOMY',
        'business': 'BUSINESS',
        'first': 'FIRST'
    }
    travel_class = cabin_class_map.get(cabin_class.lower(), 'ECONOMY')
    params['travelClass'] = travel_class
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        flights = _parse_amadeus_flights(data)
        if not flights:
            print(f"Amadeus: No flights found for {origin} to {destination} on {departure_date}")
        
        return flights
    except requests.exceptions.RequestException as e:
        print(f"Error fetching flights from Amadeus: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                print(f"Amadeus API error: {error_data}")
            except:
                print(f"Amadeus API error response: {e.response.text[:200]}")
        # Return empty list instead of mock data - let frontend handle empty state
        return []


def get_flight_details(flight_offer_id: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a specific flight offer
    
    Args:
        flight_offer_id: Amadeus flight offer ID
    
    Returns:
        Flight details dictionary or None if not found
    """
    token = _get_access_token()
    if not token:
        raise ValueError("Failed to obtain Amadeus access token")
    
    # Note: Amadeus doesn't have a direct endpoint to get flight details by ID
    # You would need to store the full offer or search again
    # This is a placeholder
    return None


def get_flight_status(flight_number: str, date: str) -> Optional[Dict[str, Any]]:
    """
    Get flight status using Amadeus Flight Status API
    
    Args:
        flight_number: Flight number (e.g., 'LH400')
        date: Flight date (YYYY-MM-DD)
    
    Returns:
        Flight status dictionary or None if not found
    """
    token = _get_access_token()
    if not token:
        raise ValueError("Failed to obtain Amadeus access token")
    
    url = f"{AMADEUS_BASE_URL}/v2/schedule/flights"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    params = {
        'carrierCode': flight_number[:2],  # Airline code
        'flightNumber': flight_number[2:],  # Flight number
        'scheduledDepartureDate': date
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching flight status from Amadeus: {e}")
        return None


def _parse_amadeus_flights(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse Amadeus API response into standardized format"""
    flights = []
    
    if 'data' in data:
        for offer in data['data']:
            # Extract pricing
            price = offer.get('price', {})
            total_price = price.get('total', '0')
            
            # Extract itineraries
            itineraries = offer.get('itineraries', [])
            if not itineraries:
                continue
            
            outbound = itineraries[0]
            segments = outbound.get('segments', [])
            
            if not segments:
                continue
            
            first_segment = segments[0]
            last_segment = segments[-1]
            
            flight = {
                'flight_id': offer.get('id'),
                'price': float(total_price) if isinstance(total_price, str) else total_price,
                'currency': price.get('currency', 'USD'),
                'airline': first_segment.get('carrierCode', ''),
                'origin': first_segment.get('departure', {}).get('iataCode', ''),
                'destination': last_segment.get('arrival', {}).get('iataCode', ''),
                'departure_date': first_segment.get('departure', {}).get('at', ''),
                'arrival_date': last_segment.get('arrival', {}).get('at', ''),
                'duration': outbound.get('duration', ''),
                'stops': len(segments) - 1,
                'direct': len(segments) == 1,
                'segments': len(segments)
            }
            
            if len(itineraries) > 1:
                return_flight = itineraries[1]
                return_segments = return_flight.get('segments', [])
                if return_segments:
                    flight['return_departure'] = return_segments[0].get('departure', {}).get('at', '')
                    flight['return_arrival'] = return_segments[-1].get('arrival', {}).get('at', '')
            
            flights.append(flight)
    
    return flights


def search_airports(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search for airports and cities using Amadeus Airport & City Search API
    
    Args:
        query: Search query (city name, airport name, or IATA code)
        limit: Maximum number of results (default: 10)
    
    Returns:
        List of airport/city dictionaries
    """
    token = _get_access_token()
    if not token:
        return []
    
    url = f"{AMADEUS_BASE_URL}/v1/reference-data/locations"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    params = {
        'subType': 'AIRPORT,CITY',
        'keyword': query,
        'max': limit
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        airports = []
        for item in data.get('data', []):
            airports.append({
                'code': item.get('iataCode', ''),
                'name': item.get('name', ''),
                'type': item.get('subType', ''),
                'city': item.get('address', {}).get('cityName', ''),
                'country': item.get('address', {}).get('countryName', ''),
                'display_name': f"{item.get('name', '')} ({item.get('iataCode', '')})"
            })
        
        return airports
    except requests.exceptions.RequestException as e:
        print(f"Error searching airports from Amadeus: {e}")
        return []


def search_flight_destinations(origin: str, max_price: Optional[float] = None, 
                               departure_date: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Flight Inspiration Search - Find destinations from an origin based on price
    
    Args:
        origin: Origin airport code (IATA)
        max_price: Maximum price in EUR
        departure_date: Optional departure date (YYYY-MM-DD)
    
    Returns:
        List of destination dictionaries with prices
    """
    token = _get_access_token()
    if not token:
        return []
    
    url = f"{AMADEUS_BASE_URL}/v1/shopping/flight-destinations"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    params = {
        'origin': origin.upper()
    }
    
    if max_price:
        params['maxPrice'] = int(max_price)
    if departure_date:
        params['departureDate'] = departure_date
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        destinations = []
        for item in data.get('data', []):
            destinations.append({
                'destination': item.get('destination', ''),
                'departure_date': item.get('departureDate', ''),
                'return_date': item.get('returnDate', ''),
                'price': float(item.get('price', {}).get('total', 0)),
                'currency': item.get('price', {}).get('currency', 'EUR')
            })
        
        return destinations
    except requests.exceptions.RequestException as e:
        print(f"Error searching flight destinations from Amadeus: {e}")
        return []


def search_cheapest_dates(origin: str, destination: str, 
                          departure_date: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Flight Cheapest Date Search - Find cheapest dates to travel
    
    Args:
        origin: Origin airport code (IATA)
        destination: Destination airport code (IATA)
        departure_date: Optional departure date range start (YYYY-MM-DD)
    
    Returns:
        List of date dictionaries with prices
    """
    token = _get_access_token()
    if not token:
        return []
    
    url = f"{AMADEUS_BASE_URL}/v1/shopping/flight-dates"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    params = {
        'origin': origin.upper(),
        'destination': destination.upper()
    }
    
    if departure_date:
        params['departureDate'] = departure_date
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        dates = []
        for item in data.get('data', []):
            dates.append({
                'departure_date': item.get('departureDate', ''),
                'return_date': item.get('returnDate', ''),
                'price': float(item.get('price', {}).get('total', 0)),
                'currency': item.get('price', {}).get('currency', 'EUR')
            })
        
        return dates
    except requests.exceptions.RequestException as e:
        print(f"Error searching cheapest dates from Amadeus: {e}")
        return []


def get_recommended_locations(city_codes: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Travel Recommendations - Get recommended destinations
    
    Args:
        city_codes: Optional list of city codes to get recommendations for
    
    Returns:
        List of recommended location dictionaries
    """
    token = _get_access_token()
    if not token:
        return []
    
    url = f"{AMADEUS_BASE_URL}/v1/reference-data/recommended-locations"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    params = {}
    if city_codes:
        params['cityCodes'] = ','.join(city_codes)
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        locations = []
        for item in data.get('data', []):
            locations.append({
                'name': item.get('name', ''),
                'iata_code': item.get('iataCode', ''),
                'geo_code': item.get('geoCode', {}),
                'category': item.get('category', '')
            })
        
        return locations
    except requests.exceptions.RequestException as e:
        print(f"Error getting recommended locations from Amadeus: {e}")
        return []


def get_seatmap(flight_offer_id: str) -> Optional[Dict[str, Any]]:
    """
    Get seat map for a flight offer
    
    Args:
        flight_offer_id: Amadeus flight offer ID
    
    Returns:
        Seat map dictionary or None if not found
    """
    token = _get_access_token()
    if not token:
        return None
    
    url = f"{AMADEUS_BASE_URL}/v1/shopping/seatmaps"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    params = {
        'flight-orderId': flight_offer_id
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching seat map from Amadeus: {e}")
        return None


def price_flight_offer(flight_offer: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Confirm flight offer pricing before booking
    
    Args:
        flight_offer: Flight offer object from search
    
    Returns:
        Priced flight offer or None if pricing failed
    """
    token = _get_access_token()
    if not token:
        return None
    
    url = f"{AMADEUS_BASE_URL}/v1/shopping/flight-offers/pricing"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/vnd.amadeus+json'
    }
    
    payload = {
        'data': {
            'type': 'flight-offers-pricing',
            'flightOffers': [flight_offer]
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error pricing flight offer from Amadeus: {e}")
        return None


def search_activities(latitude: float, longitude: float, radius: int = 5) -> List[Dict[str, Any]]:
    """
    Search for tours and activities near a location
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        radius: Search radius in kilometers (default: 5)
    
    Returns:
        List of activity dictionaries
    """
    token = _get_access_token()
    if not token:
        return []
    
    url = f"{AMADEUS_BASE_URL}/v1/shopping/activities"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    params = {
        'latitude': latitude,
        'longitude': longitude,
        'radius': radius
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        activities = []
        for item in data.get('data', []):
            activities.append({
                'id': item.get('id', ''),
                'name': item.get('name', ''),
                'description': item.get('shortDescription', ''),
                'price': float(item.get('price', {}).get('amount', 0)) if item.get('price') else 0,
                'currency': item.get('price', {}).get('currencyCode', 'USD') if item.get('price') else 'USD',
                'rating': item.get('rating', 0),
                'pictures': item.get('pictures', []),
                'bookingLink': item.get('bookingLink', '')
            })
        
        return activities
    except requests.exceptions.RequestException as e:
        print(f"Error searching activities from Amadeus: {e}")
        return []


def get_most_traveled_destinations(origin: str, period: str = '2024-01') -> List[Dict[str, Any]]:
    """
    Get most traveled destinations from an origin
    
    Args:
        origin: Origin airport code (IATA)
        period: Period in YYYY-MM format
    
    Returns:
        List of destination dictionaries with travel statistics
    """
    token = _get_access_token()
    if not token:
        return []
    
    url = f"{AMADEUS_BASE_URL}/v1/travel/analytics/air-traffic/traveled"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    params = {
        'originCityCode': origin.upper(),
        'period': period
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        destinations = []
        for item in data.get('data', []):
            destinations.append({
                'destination': item.get('destination', ''),
                'analytics': item.get('analytics', {})
            })
        
        return destinations
    except requests.exceptions.RequestException as e:
        print(f"Error getting most traveled destinations from Amadeus: {e}")
        return []


def _get_mock_flights(origin: str, destination: str, departure_date: str, 
                     return_date: Optional[str], passengers: int) -> List[Dict[str, Any]]:
    """Mock flight data for development/testing"""
    flights = []
    airlines = ['AA', 'DL', 'UA', 'WN', 'B6']
    airline_names = ['American Airlines', 'Delta', 'United', 'Southwest', 'JetBlue']
    
    for i in range(5):
        flight = {
            'flight_id': f'amadeus_flight_{i}',
            'airline': airline_names[i % len(airline_names)],
            'airline_code': airlines[i % len(airlines)],
            'origin': origin,
            'destination': destination,
            'departure_date': departure_date,
            'departure_time': f'{8 + i}:00',
            'arrival_time': f'{10 + i}:30',
            'duration': f'PT{2 + i}H{30 + i * 10}M',
            'price': 200 + i * 50,
            'currency': 'USD',
            'cabin_class': 'ECONOMY',
            'stops': 0 if i < 2 else 1,
            'direct': i < 2,
            'passengers': passengers
        }
        
        if return_date:
            flight['return_date'] = return_date
            flight['return_departure_time'] = f'{14 + i}:00'
            flight['return_arrival_time'] = f'{16 + i}:30'
        
        flights.append(flight)
    
    return flights

