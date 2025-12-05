"""
Airport search service using a comprehensive airport database
"""
from typing import List, Dict, Any
import json
import os


def search_airports(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search for airports using a comprehensive airport database
    
    Args:
        query: Search query (city name, airport name, or IATA code)
        limit: Maximum number of results (default: 10)
    
    Returns:
        List of airport/city dictionaries
    """
    try:
        query_upper = query.upper().strip()
        query_lower = query.lower().strip()
        
        # If it's a 3-letter code, search by IATA code
        if len(query_upper) == 3 and query_upper.isalpha():
            airports = _search_by_iata_code(query_upper)
            if airports:
                return airports[:limit]
        
        # Search by name/city
        airports = _search_by_name(query_lower)
        return airports[:limit]
        
    except Exception as e:
        print(f"Error searching airports: {e}")
        return []


def _get_airport_database() -> Dict[str, Dict[str, Any]]:
    """Get comprehensive airport database"""
    return {
        # US Major Airports
        'ATL': {'name': 'Hartsfield-Jackson Atlanta International Airport', 'city': 'Atlanta', 'country': 'United States'},
        'JFK': {'name': 'John F. Kennedy International Airport', 'city': 'New York', 'country': 'United States'},
        'LAX': {'name': 'Los Angeles International Airport', 'city': 'Los Angeles', 'country': 'United States'},
        'ORD': {'name': "O'Hare International Airport", 'city': 'Chicago', 'country': 'United States'},
        'DFW': {'name': 'Dallas/Fort Worth International Airport', 'city': 'Dallas', 'country': 'United States'},
        'DEN': {'name': 'Denver International Airport', 'city': 'Denver', 'country': 'United States'},
        'SFO': {'name': 'San Francisco International Airport', 'city': 'San Francisco', 'country': 'United States'},
        'SEA': {'name': 'Seattle-Tacoma International Airport', 'city': 'Seattle', 'country': 'United States'},
        'LAS': {'name': 'Harry Reid International Airport', 'city': 'Las Vegas', 'country': 'United States'},
        'MIA': {'name': 'Miami International Airport', 'city': 'Miami', 'country': 'United States'},
        'BOS': {'name': 'Logan International Airport', 'city': 'Boston', 'country': 'United States'},
        'IAH': {'name': 'George Bush Intercontinental Airport', 'city': 'Houston', 'country': 'United States'},
        'MSP': {'name': 'Minneapolis-Saint Paul International Airport', 'city': 'Minneapolis', 'country': 'United States'},
        'DTW': {'name': 'Detroit Metropolitan Airport', 'city': 'Detroit', 'country': 'United States'},
        'PHX': {'name': 'Phoenix Sky Harbor International Airport', 'city': 'Phoenix', 'country': 'United States'},
        'LGA': {'name': 'LaGuardia Airport', 'city': 'New York', 'country': 'United States'},
        'EWR': {'name': 'Newark Liberty International Airport', 'city': 'Newark', 'country': 'United States'},
        'BWI': {'name': 'Baltimore-Washington International Airport', 'city': 'Baltimore', 'country': 'United States'},
        'DCA': {'name': 'Ronald Reagan Washington National Airport', 'city': 'Washington', 'country': 'United States'},
        'IAD': {'name': 'Washington Dulles International Airport', 'city': 'Washington', 'country': 'United States'},
        'SLC': {'name': 'Salt Lake City International Airport', 'city': 'Salt Lake City', 'country': 'United States'},
        'PDX': {'name': 'Portland International Airport', 'city': 'Portland', 'country': 'United States'},
        'HNL': {'name': 'Daniel K. Inouye International Airport', 'city': 'Honolulu', 'country': 'United States'},
        
        # European Airports
        'LHR': {'name': 'London Heathrow Airport', 'city': 'London', 'country': 'United Kingdom'},
        'LGW': {'name': 'London Gatwick Airport', 'city': 'London', 'country': 'United Kingdom'},
        'CDG': {'name': 'Charles de Gaulle Airport', 'city': 'Paris', 'country': 'France'},
        'ORY': {'name': 'Orly Airport', 'city': 'Paris', 'country': 'France'},
        'FRA': {'name': 'Frankfurt Airport', 'city': 'Frankfurt', 'country': 'Germany'},
        'MUC': {'name': 'Munich Airport', 'city': 'Munich', 'country': 'Germany'},
        'AMS': {'name': 'Amsterdam Airport Schiphol', 'city': 'Amsterdam', 'country': 'Netherlands'},
        'MAD': {'name': 'Madrid-Barajas Airport', 'city': 'Madrid', 'country': 'Spain'},
        'BCN': {'name': 'Barcelona-El Prat Airport', 'city': 'Barcelona', 'country': 'Spain'},
        'FCO': {'name': 'Leonardo da Vinci-Fiumicino Airport', 'city': 'Rome', 'country': 'Italy'},
        'MXP': {'name': 'Milan Malpensa Airport', 'city': 'Milan', 'country': 'Italy'},
        'ZUR': {'name': 'Zurich Airport', 'city': 'Zurich', 'country': 'Switzerland'},
        'VIE': {'name': 'Vienna International Airport', 'city': 'Vienna', 'country': 'Austria'},
        'CPH': {'name': 'Copenhagen Airport', 'city': 'Copenhagen', 'country': 'Denmark'},
        'ARN': {'name': 'Stockholm Arlanda Airport', 'city': 'Stockholm', 'country': 'Sweden'},
        'OSL': {'name': 'Oslo Gardermoen Airport', 'city': 'Oslo', 'country': 'Norway'},
        'DUB': {'name': 'Dublin Airport', 'city': 'Dublin', 'country': 'Ireland'},
        'LIS': {'name': 'Lisbon Portela Airport', 'city': 'Lisbon', 'country': 'Portugal'},
        'ATH': {'name': 'Athens International Airport', 'city': 'Athens', 'country': 'Greece'},
        'IST': {'name': 'Istanbul Airport', 'city': 'Istanbul', 'country': 'Turkey'},
        
        # Asian Airports
        'DXB': {'name': 'Dubai International Airport', 'city': 'Dubai', 'country': 'United Arab Emirates'},
        'AUH': {'name': 'Abu Dhabi International Airport', 'city': 'Abu Dhabi', 'country': 'United Arab Emirates'},
        'DOH': {'name': 'Hamad International Airport', 'city': 'Doha', 'country': 'Qatar'},
        'NRT': {'name': 'Narita International Airport', 'city': 'Tokyo', 'country': 'Japan'},
        'HND': {'name': 'Haneda Airport', 'city': 'Tokyo', 'country': 'Japan'},
        'ICN': {'name': 'Incheon International Airport', 'city': 'Seoul', 'country': 'South Korea'},
        'PEK': {'name': 'Beijing Capital International Airport', 'city': 'Beijing', 'country': 'China'},
        'PVG': {'name': 'Shanghai Pudong International Airport', 'city': 'Shanghai', 'country': 'China'},
        'HKG': {'name': 'Hong Kong International Airport', 'city': 'Hong Kong', 'country': 'China'},
        'SIN': {'name': 'Singapore Changi Airport', 'city': 'Singapore', 'country': 'Singapore'},
        'BKK': {'name': 'Suvarnabhumi Airport', 'city': 'Bangkok', 'country': 'Thailand'},
        'KUL': {'name': 'Kuala Lumpur International Airport', 'city': 'Kuala Lumpur', 'country': 'Malaysia'},
        'BOM': {'name': 'Chhatrapati Shivaji Maharaj International Airport', 'city': 'Mumbai', 'country': 'India'},
        'DEL': {'name': 'Indira Gandhi International Airport', 'city': 'New Delhi', 'country': 'India'},
        
        # Other Major Airports
        'SYD': {'name': 'Sydney Kingsford Smith Airport', 'city': 'Sydney', 'country': 'Australia'},
        'MEL': {'name': 'Melbourne Airport', 'city': 'Melbourne', 'country': 'Australia'},
        'YYZ': {'name': 'Toronto Pearson International Airport', 'city': 'Toronto', 'country': 'Canada'},
        'YVR': {'name': 'Vancouver International Airport', 'city': 'Vancouver', 'country': 'Canada'},
        'GRU': {'name': 'São Paulo-Guarulhos International Airport', 'city': 'São Paulo', 'country': 'Brazil'},
        'GIG': {'name': 'Rio de Janeiro-Galeão International Airport', 'city': 'Rio de Janeiro', 'country': 'Brazil'},
        'MEX': {'name': 'Mexico City International Airport', 'city': 'Mexico City', 'country': 'Mexico'},
        'JNB': {'name': 'O. R. Tambo International Airport', 'city': 'Johannesburg', 'country': 'South Africa'},
    }


def _search_by_iata_code(code: str) -> List[Dict[str, Any]]:
    """Search airports by IATA code"""
    airports_db = _get_airport_database()
    
    if code in airports_db:
        airport = airports_db[code]
        return [{
            'code': code,
            'name': airport['name'],
            'type': 'AIRPORT',
            'city': airport['city'],
            'country': airport['country'],
            'display_name': f"{airport['name']} ({code})"
        }]
    
    return []


def _search_by_name(query: str) -> List[Dict[str, Any]]:
    """Search airports by city/airport name"""
    query_lower = query.lower().strip()
    results = []
    seen_codes = set()
    
    airports_db = _get_airport_database()
    
    # Group airports by city for city-based search
    city_airports: Dict[str, List[str]] = {}
    for code, airport in airports_db.items():
        city = airport['city'].lower()
        if city not in city_airports:
            city_airports[city] = []
        city_airports[city].append(code)
    
    # Search by city name
    for city, codes in city_airports.items():
        if query_lower in city or city.startswith(query_lower):
            for code in codes:
                if code not in seen_codes:
                    airport = airports_db[code]
                    results.append({
                        'code': code,
                        'name': airport['name'],
                        'type': 'AIRPORT',
                        'city': airport['city'],
                        'country': airport['country'],
                        'display_name': f"{airport['name']} ({code})"
                    })
                    seen_codes.add(code)
    
    # Search by airport name
    for code, airport in airports_db.items():
        if code in seen_codes:
            continue
        airport_name_lower = airport['name'].lower()
        if query_lower in airport_name_lower or airport_name_lower.startswith(query_lower):
            results.append({
                'code': code,
                'name': airport['name'],
                'type': 'AIRPORT',
                'city': airport['city'],
                'country': airport['country'],
                'display_name': f"{airport['name']} ({code})"
            })
            seen_codes.add(code)
    
    return results

