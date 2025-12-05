"""
SerpAPI Google Flights integration for flight search
"""
import os
import requests
from typing import Optional, Dict, List, Any

SERPAPI_API_KEY = os.getenv('SERP_API_KEY')
SERPAPI_BASE_URL = 'https://serpapi.com/search'


def search_flights(origin: str, destination: str, departure_date: str, 
                  return_date: Optional[str] = None, passengers: int = 1,
                  cabin_class: str = 'ECONOMY') -> List[Dict[str, Any]]:
    """
    Search for flights using SerpAPI Google Flights API
    
    Args:
        origin: Origin airport code (IATA) - 3-letter uppercase code
        destination: Destination airport code (IATA) - 3-letter uppercase code
        departure_date: Departure date (YYYY-MM-DD)
        return_date: Optional return date (YYYY-MM-DD) for round trips
        passengers: Number of passengers (default: 1)
        cabin_class: Cabin class ('ECONOMY', 'PREMIUM_ECONOMY', 'BUSINESS', 'FIRST')
    
    Returns:
        List of flight dictionaries in standardized format
    """
    if not SERPAPI_API_KEY:
        raise ValueError("SERP_API_KEY must be set in environment variables")
    
    # Clean and validate airport codes
    origin = origin.upper().strip().replace(' ', '').replace('+', '')
    destination = destination.upper().strip().replace(' ', '').replace('+', '')
    
    # Validate that we have 3-letter airport codes (or location kgmid starting with /m/)
    def is_valid_airport_id(code: str) -> bool:
        return (len(code) == 3 and code.isalpha()) or code.startswith('/m/')
    
    if not is_valid_airport_id(origin):
        raise ValueError(f"Invalid origin airport code: '{origin}'. Must be a 3-letter IATA code (e.g., ATL, JFK) or select from airport suggestions.")
    
    if not is_valid_airport_id(destination):
        raise ValueError(f"Invalid destination airport code: '{destination}'. Must be a 3-letter IATA code (e.g., ATL, JFK) or select from airport suggestions.")
    
    # Map cabin class to SerpAPI numeric values
    cabin_class_map = {
        'economy': '1',
        'premium': '2',
        'premium_economy': '2',
        'business': '3',
        'first': '4'
    }
    travel_class = cabin_class_map.get(cabin_class.lower(), '1')
    
    # Determine flight type
    flight_type = '1' if return_date else '2'  # 1 = Round trip, 2 = One way
    
    params = {
        'engine': 'google_flights',
        'api_key': SERPAPI_API_KEY,
        'departure_id': origin,
        'arrival_id': destination,
        'outbound_date': departure_date,
        'adults': passengers,
        'travel_class': travel_class,
        'type': flight_type,
        'currency': 'USD',
        'hl': 'en',
        'gl': 'us'
    }
    
    if return_date:
        params['return_date'] = return_date
    
    try:
        response = requests.get(SERPAPI_BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        flights = _parse_serpapi_flights(data, return_date is not None)
        
        if not flights:
            print(f"SerpAPI: No flights found for {origin} to {destination} on {departure_date}")
        
        return flights
    except requests.exceptions.RequestException as e:
        print(f"Error fetching flights from SerpAPI: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                print(f"SerpAPI error: {error_data}")
            except:
                print(f"SerpAPI error response: {e.response.text[:200]}")
        return []


def _parse_serpapi_flights_with_returns(outbound_data: Dict[str, Any], origin: str, 
                                       destination: str, return_date: str, 
                                       passengers: int, travel_class: str) -> List[Dict[str, Any]]:
    """Parse round trip flights - fetch return flights for each outbound option"""
    all_flights = []
    
    # Get outbound flights
    outbound_flights_list = []
    if 'best_flights' in outbound_data:
        outbound_flights_list.extend(outbound_data['best_flights'])
    if 'other_flights' in outbound_data:
        outbound_flights_list.extend(outbound_data['other_flights'])
    
    # For each outbound flight, fetch return flights
    for outbound_flight in outbound_flights_list[:10]:  # Limit to first 10 to avoid too many API calls
        departure_token = outbound_flight.get('departure_token')
        if not departure_token:
            continue
        
        # Fetch return flights
        return_params = {
            'engine': 'google_flights',
            'api_key': SERPAPI_API_KEY,
            'departure_id': destination.upper(),
            'arrival_id': origin.upper(),
            'outbound_date': return_date,
            'adults': passengers,
            'travel_class': travel_class,
            'type': '2',  # One way for return
            'departure_token': departure_token,
            'currency': 'USD',
            'hl': 'en',
            'gl': 'us'
        }
        
        try:
            return_response = requests.get(SERPAPI_BASE_URL, params=return_params, timeout=30)
            return_response.raise_for_status()
            return_data = return_response.json()
            
            # Get return flight options
            return_flights_list = []
            if 'best_flights' in return_data:
                return_flights_list.extend(return_data['best_flights'])
            if 'other_flights' in return_data:
                return_flights_list.extend(return_data['other_flights'])
            
            # Combine outbound with each return option
            for return_flight in return_flights_list[:3]:  # Limit to top 3 return options
                combined_flight = _combine_round_trip_flights(outbound_flight, return_flight)
                if combined_flight:
                    all_flights.append(combined_flight)
        except Exception as e:
            print(f"Error fetching return flights: {e}")
            continue
    
    return all_flights


def _combine_round_trip_flights(outbound: Dict[str, Any], return_flight: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Combine outbound and return flights into a single round trip flight object"""
    outbound_segments = outbound.get('flights', [])
    return_segments = return_flight.get('flights', [])
    
    if not outbound_segments or not return_segments:
        return None
    
    first_outbound = outbound_segments[0]
    last_outbound = outbound_segments[-1]
    first_return = return_segments[0]
    last_return = return_segments[-1]
    
    # Calculate total price
    outbound_price = outbound.get('price', 0)
    return_price = return_flight.get('price', 0)
    total_price = (outbound_price or 0) + (return_price or 0)
    
    # Total duration
    outbound_duration = outbound.get('total_duration', 0)
    return_duration = return_flight.get('total_duration', 0)
    total_duration = outbound_duration + return_duration
    duration_hours = total_duration // 60
    duration_mins = total_duration % 60
    duration_str = f"PT{duration_hours}H{duration_mins}M"
    
    flight = {
        'flight_id': outbound.get('booking_token', '') or outbound.get('departure_token', ''),
        'price': float(total_price) if total_price else 0,
        'currency': 'USD',
        'airline': first_outbound.get('airline', ''),
        'origin': first_outbound.get('departure_airport', {}).get('id', ''),
        'destination': last_outbound.get('arrival_airport', {}).get('id', ''),
        'departure_date': first_outbound.get('departure_airport', {}).get('time', ''),
        'arrival_date': last_outbound.get('arrival_airport', {}).get('time', ''),
        'return_departure': first_return.get('departure_airport', {}).get('time', ''),
        'return_arrival': last_return.get('arrival_airport', {}).get('time', ''),
        'duration': duration_str,
        'stops': len(outbound.get('layovers', [])),
        'return_stops': len(return_flight.get('layovers', [])),
        'direct': len(outbound_segments) == 1,
        'return_direct': len(return_segments) == 1,
        'segments': len(outbound_segments),
        'return_segments': len(return_segments),
        'layovers': [
            {
                'airport': layover.get('name', ''),
                'code': layover.get('id', ''),
                'duration_minutes': layover.get('duration', 0)
            }
            for layover in outbound.get('layovers', [])
        ],
        'return_layovers': [
            {
                'airport': layover.get('name', ''),
                'code': layover.get('id', ''),
                'duration_minutes': layover.get('duration', 0)
            }
            for layover in return_flight.get('layovers', [])
        ],
        'carbon_emissions': outbound.get('carbon_emissions', {}).get('this_flight'),
        'extensions': outbound.get('extensions', [])
    }
    
    return flight


def _parse_serpapi_flights(data: Dict[str, Any], is_round_trip: bool) -> List[Dict[str, Any]]:
    """Parse SerpAPI Google Flights response into standardized format"""
    flights = []
    
    # Combine best_flights and other_flights
    all_flights = []
    if 'best_flights' in data:
        all_flights.extend(data['best_flights'])
    if 'other_flights' in data:
        all_flights.extend(data['other_flights'])
    
    for flight_option in all_flights:
        flight_segments = flight_option.get('flights', [])
        if not flight_segments:
            continue
        
        # Extract outbound flight information
        first_segment = flight_segments[0]
        last_segment = flight_segments[-1]
        
        departure_airport = first_segment.get('departure_airport', {})
        arrival_airport = last_segment.get('arrival_airport', {})
        
        # Calculate total duration
        total_duration_minutes = flight_option.get('total_duration', 0)
        duration_hours = total_duration_minutes // 60
        duration_mins = total_duration_minutes % 60
        duration_str = f"PT{duration_hours}H{duration_mins}M"
        
        # Count stops
        layovers = flight_option.get('layovers', [])
        stops = len(layovers)
        
        # Get price
        price = flight_option.get('price', 0)
        
        # Build flight object
        flight = {
            'flight_id': flight_option.get('booking_token', '') or flight_option.get('departure_token', ''),
            'price': float(price) if price else 0,
            'currency': 'USD',
            'airline': first_segment.get('airline', ''),
            'origin': departure_airport.get('id', ''),
            'destination': arrival_airport.get('id', ''),
            'departure_date': departure_airport.get('time', ''),
            'arrival_date': arrival_airport.get('time', ''),
            'duration': duration_str,
            'stops': stops,
            'direct': stops == 0,
            'segments': len(flight_segments),
            'layovers': [
                {
                    'airport': layover.get('name', ''),
                    'code': layover.get('id', ''),
                    'duration_minutes': layover.get('duration', 0)
                }
                for layover in layovers
            ],
            'carbon_emissions': flight_option.get('carbon_emissions', {}).get('this_flight'),
            'extensions': flight_option.get('extensions', [])
        }
        
        # For round trips, extract return flight info if available in the same response
        if is_round_trip:
            # Check if there are return flights in the segments (multi-segment round trip)
            # Or if we need to use departure_token for a separate request
            if 'departure_token' in flight_option:
                flight['return_token'] = flight_option.get('departure_token')
            # Note: For complete round trip data, SerpAPI may require a second request
            # This is handled by the frontend or can be enhanced later
        
        # Add segment details
        flight['segment_details'] = [
            {
                'airline': seg.get('airline', ''),
                'flight_number': seg.get('flight_number', ''),
                'departure_airport': seg.get('departure_airport', {}).get('id', ''),
                'arrival_airport': seg.get('arrival_airport', {}).get('id', ''),
                'departure_time': seg.get('departure_airport', {}).get('time', ''),
                'arrival_time': seg.get('arrival_airport', {}).get('time', ''),
                'duration_minutes': seg.get('duration', 0),
                'airplane': seg.get('airplane', ''),
                'travel_class': seg.get('travel_class', '')
            }
            for seg in flight_segments
        ]
        
        flights.append(flight)
    
    return flights


def get_flight_details(flight_token: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a specific flight using booking token
    
    Args:
        flight_token: SerpAPI booking token from flight search results
    
    Returns:
        Flight details dictionary or None if not found
    """
    if not SERPAPI_API_KEY:
        return None
    
    params = {
        'engine': 'google_flights',
        'api_key': SERPAPI_API_KEY,
        'booking_token': flight_token,
        'currency': 'USD',
        'hl': 'en'
    }
    
    try:
        response = requests.get(SERPAPI_BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Parse booking options from response
        # Note: SerpAPI booking token response structure may vary
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching flight details from SerpAPI: {e}")
        return None

