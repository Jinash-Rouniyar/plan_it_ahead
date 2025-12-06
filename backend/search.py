from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from services.opentripmap import search_pois, get_poi_details, get_nearby_pois
from services.image_search import search_image
from services.serpapi_tripadvisor import search_tripadvisor, SERPAPI_API_KEY as SERP_TRIP_API_KEY
from services.xotelo import search_hotels, get_hotel_details, get_pricing, get_hotel_heatmap
from services.serpapi_tripadvisor import search_tripadvisor_hotels, SERPAPI_API_KEY as SERP_TRIP_API_KEY
from services.serpapi_flights import search_flights, get_flight_details
from services.airport_search import search_airports
from services.amadeus import (
    get_flight_status,
    search_flight_destinations, search_cheapest_dates, get_recommended_locations,
    get_seatmap, price_flight_offer, search_activities, get_most_traveled_destinations
)
from services.wikivoyage import get_destination_guide, get_travel_tips, search_destinations

bp = Blueprint('search', __name__, url_prefix='/api/search')


@bp.route('/destinations', methods=['GET'])
@jwt_required(optional=True)
def search_destinations():
    query = request.args.get('query', '').strip()
    
    if not query:
        return jsonify({'msg': 'query parameter required'}), 400
    
    try:
        from services.opentripmap import OPENTRIPMAP_BASE_URL, OPENTRIPMAP_API_KEY
        import requests
        
        if not OPENTRIPMAP_API_KEY:
            return jsonify({'msg': 'OpenTripMap API key not configured'}), 500
        
        url = f"{OPENTRIPMAP_BASE_URL}/places/geoname"
        params = {
            'name': query,
            'apikey': OPENTRIPMAP_API_KEY
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data:
            destinations = [{
                'name': data.get('name', query),
                'country': data.get('country', ''),
                'lat': data.get('lat'),
                'lon': data.get('lon'),
                'type': 'city' if data.get('fcode', '').startswith('PPL') else 'location'
            }]
        else:
            destinations = []
        
        return jsonify({'destinations': destinations}), 200
    
    except Exception as e:
        print(f"Error searching destinations: {e}")
        return jsonify({'msg': 'Error searching destinations', 'error': str(e)}), 500


@bp.route('/attractions', methods=['GET'])
@jwt_required(optional=True)
def search_attractions():
    location = request.args.get('location', '').strip()
    category = request.args.get('category')
    radius = request.args.get('radius', 5000, type=int)
    limit = request.args.get('limit', 20, type=int)
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    
    try:
        if lat and lon:
            pois = get_nearby_pois(lat, lon, radius, category, limit)
        elif location:
            pois = search_pois(location, category, radius, limit)
        else:
            return jsonify({'msg': 'location or lat/lon required'}), 400
        formatted_pois = []
        for poi in pois:
            if isinstance(poi, dict):
                props = poi.get('properties', {})
                geom = poi.get('geometry', {})
                coords = geom.get('coordinates', [])
                
                formatted_poi = {
                    'xid': props.get('xid'),
                    'name': props.get('name', 'Unknown'),
                    'category': props.get('kinds', '').split(',')[0] if props.get('kinds') else '',
                    'description': props.get('wikipedia_extracts', {}).get('text', '')[:200] if props.get('wikipedia_extracts') else '',
                    'lat': coords[1] if len(coords) > 1 else None,
                    'lon': coords[0] if len(coords) > 0 else None,
                    'distance': props.get('dist', 0),
                    'rate': props.get('rate', 0),
                    'image_url': props.get('preview', {}).get('source') if props.get('preview') else None
                }
                formatted_pois.append(formatted_poi)
        
        if not formatted_pois:
            return jsonify({
                'attractions': [],
                'count': 0,
                'msg': 'No attractions found. Try a different location or increase the search radius.'
            }), 200
        
        return jsonify({
            'attractions': formatted_pois,
            'count': len(formatted_pois)
        }), 200
    
    except Exception as e:
        print(f"Error searching attractions: {e}")
        return jsonify({'msg': 'Error searching attractions', 'error': str(e)}), 500


@bp.route('/attractions/<xid>', methods=['GET'])
@jwt_required(optional=True)
def get_attraction_details(xid):
    try:
        details = get_poi_details(xid)
        if not details:
            return jsonify({'msg': 'Attraction not found'}), 404
        
        formatted = {
            'xid': details.get('xid'),
            'name': details.get('name', 'Unknown'),
            'address': details.get('address', {}).get('display', '') if details.get('address') else '',
            'description': details.get('wikipedia_extracts', {}).get('text', '') if details.get('wikipedia_extracts') else '',
            'categories': details.get('kinds', '').split(',') if details.get('kinds') else [],
            'lat': details.get('point', {}).get('lat') if details.get('point') else None,
            'lon': details.get('point', {}).get('lon') if details.get('point') else None,
            'image_url': details.get('preview', {}).get('source') if details.get('preview') else None,
            'url': details.get('url'),
            'rate': details.get('rate', 0),
            'wikipedia': details.get('wikipedia', '')
        }
        
        return jsonify(formatted), 200
    
    except Exception as e:
        print(f"Error fetching attraction details: {e}")
        return jsonify({'msg': 'Error fetching attraction details', 'error': str(e)}), 500


@bp.route('/attractions-serp', methods=['GET'])
@jwt_required(optional=True)
def search_attractions_serp():
    """Search attractions and enrich with SerpAPI images when available"""
    location = request.args.get('location', '').strip()
    radius = request.args.get('radius', 5000, type=int)
    limit = request.args.get('limit', 20, type=int)
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)

    try:
        formatted = []

        # Prefer SerpAPI TripAdvisor search when API key available
        if SERP_TRIP_API_KEY:
            try:
                serp_results = search_tripadvisor(location or query, location, limit)
                if serp_results:
                    for r in serp_results:
                        formatted.append({
                            'xid': None,
                            'name': r.get('name'),
                            'type': r.get('type'),
                            'description': (r.get('description') or '')[:300],
                            'lat': r.get('lat'),
                            'lon': r.get('lon'),
                            'image_url': r.get('image_url'),
                            'rate': r.get('rate') or 0,
                            'distance': 0
                        })
                    return jsonify({'attractions': formatted, 'count': len(formatted)}), 200
            except Exception:
                # fallback to OpenTripMap below
                formatted = []

        # Fallback: use OpenTripMap POIs and optionally enrich images via SerpAPI image search
        if lat and lon:
            pois = get_nearby_pois(lat, lon, radius, None, limit)
        elif location:
            pois = search_pois(location, None, radius, limit)
        else:
            return jsonify({'msg': 'location or lat/lon required'}), 400

        for poi in pois:
            if isinstance(poi, dict):
                props = poi.get('properties', {})
                geom = poi.get('geometry', {})
                coords = geom.get('coordinates', [])
                name = props.get('name', 'Unknown')
                desc = props.get('wikipedia_extracts', {}).get('text', '') if props.get('wikipedia_extracts') else ''
                image_url = props.get('preview', {}).get('source') if props.get('preview') else None

                # If no preview image, try SerpAPI image search
                if not image_url:
                    try:
                        img = search_image(name, location)
                        if img:
                            image_url = img
                    except Exception:
                        image_url = None

                formatted.append({
                    'xid': props.get('xid'),
                    'name': name,
                    'type': props.get('kinds', '').split(',')[0] if props.get('kinds') else '',
                    'description': (desc or '')[:300],
                    'lat': coords[1] if len(coords) > 1 else None,
                    'lon': coords[0] if len(coords) > 0 else None,
                    'image_url': image_url,
                    'rate': props.get('rate', 0),
                    'distance': props.get('dist', 0)
                })

        return jsonify({'attractions': formatted, 'count': len(formatted)}), 200
    except Exception as e:
        print(f"Error searching attractions with Serp enrichment: {e}")
        return jsonify({'msg': 'Error searching attractions', 'error': str(e)}), 500


@bp.route('/hotels', methods=['GET'])
@jwt_required(optional=True)
def search_hotels_endpoint():
    location = request.args.get('location', '').strip()
    check_in = request.args.get('check_in', '').strip()
    check_out = request.args.get('check_out', '').strip()
    guests = request.args.get('guests', 2, type=int)
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    limit = request.args.get('limit', 20, type=int)
    
    if not location:
        return jsonify({'msg': 'location parameter required'}), 400
    if not check_in or not check_out:
        return jsonify({'msg': 'check_in and check_out parameters required'}), 400
    
    try:
        # Prefer SerpAPI TripAdvisor results when available
        if SERP_TRIP_API_KEY:
            try:
                serp_hotels = search_tripadvisor_hotels(location, location, limit)
                if serp_hotels:
                    return jsonify({'hotels': serp_hotels, 'count': len(serp_hotels)}), 200
            except Exception:
                pass

        hotels = search_hotels(location, check_in, check_out, guests, min_price, max_price, limit)

        if not hotels:
            return jsonify({
                'hotels': [],
                'count': 0,
                'msg': 'No hotels found. Try adjusting your search criteria.'
            }), 200

        return jsonify({
            'hotels': hotels,
            'count': len(hotels)
        }), 200

    except Exception as e:
        print(f"Error searching hotels: {e}")
        return jsonify({'msg': 'Error searching hotels', 'error': str(e)}), 500


@bp.route('/hotels/<hotel_id>', methods=['GET'])
@jwt_required(optional=True)
def get_hotel_details_endpoint(hotel_id):
    try:
        details = get_hotel_details(hotel_id)
        if not details:
            return jsonify({'msg': 'Hotel not found'}), 404
        
        return jsonify(details), 200
    
    except Exception as e:
        print(f"Error fetching hotel details: {e}")
        return jsonify({'msg': 'Error fetching hotel details', 'error': str(e)}), 500


@bp.route('/hotels/<hotel_key>/pricing', methods=['GET'])
@jwt_required(optional=True)
def get_hotel_pricing(hotel_key):
    """Get latest pricing for a hotel for specific dates using Xotelo"""
    check_in = request.args.get('check_in', '').strip()
    check_out = request.args.get('check_out', '').strip()
    guests = request.args.get('guests', 2, type=int)
    rooms = request.args.get('rooms', 1, type=int)
    currency = request.args.get('currency', 'USD')
    
    if not check_in or not check_out:
        return jsonify({'msg': 'check_in and check_out parameters required'}), 400
    
    try:
        pricing = get_pricing(hotel_key, check_in, check_out, guests, rooms, currency)
        if not pricing:
            return jsonify({'msg': 'Pricing not available'}), 404
        
        return jsonify(pricing), 200
    
    except Exception as e:
        print(f"Error fetching hotel pricing: {e}")
        return jsonify({'msg': 'Error fetching hotel pricing', 'error': str(e)}), 500


@bp.route('/hotels/<hotel_key>/heatmap', methods=['GET'])
@jwt_required(optional=True)
def get_hotel_heatmap_endpoint(hotel_key):
    """Get hotel pricing heatmap for a specific hotel using Xotelo"""
    check_out = request.args.get('check_out', '').strip()
    
    if not check_out:
        return jsonify({'msg': 'check_out parameter required'}), 400
    
    try:
        heatmap = get_hotel_heatmap(hotel_key, check_out)
        if not heatmap:
            return jsonify({'msg': 'Heatmap not available'}), 404
        
        return jsonify(heatmap), 200
    
    except Exception as e:
        print(f"Error fetching hotel heatmap: {e}")
        return jsonify({'msg': 'Error fetching hotel heatmap', 'error': str(e)}), 500


@bp.route('/airports', methods=['GET'])
@jwt_required(optional=True)
def search_airports_endpoint():
    query = request.args.get('query', '').strip()
    limit = request.args.get('limit', 10, type=int)
    
    if not query:
        return jsonify({'msg': 'query parameter required'}), 400
    
    try:
        airports = search_airports(query, limit)
        return jsonify({
            'airports': airports,
            'count': len(airports)
        }), 200
    except Exception as e:
        print(f"Error searching airports: {e}")
        return jsonify({'msg': 'Error searching airports', 'error': str(e)}), 500


@bp.route('/flights', methods=['GET'])
@jwt_required(optional=True)
def search_flights_endpoint():
    origin = request.args.get('origin', '').strip()
    destination = request.args.get('destination', '').strip()
    departure_date = request.args.get('departure_date', '').strip()
    return_date = request.args.get('return_date', '').strip() or None
    passengers = request.args.get('passengers', 1, type=int)
    cabin_class = request.args.get('cabin_class', 'economy')
    
    if not origin or not destination or not departure_date:
        return jsonify({'msg': 'origin, destination, and departure_date parameters required'}), 400
    
    try:
        flights = search_flights(origin, destination, departure_date, return_date, passengers, cabin_class)
        
        if not flights:
            return jsonify({
                'flights': [],
                'count': 0,
                'msg': 'No flights found. Try different dates or airports.'
            }), 200
        
        return jsonify({
            'flights': flights,
            'count': len(flights)
        }), 200
    
    except ValueError as e:
        print(f"Validation error searching flights: {e}")
        return jsonify({'msg': str(e)}), 400
    except Exception as e:
        print(f"Error searching flights: {e}")
        return jsonify({'msg': 'Error searching flights', 'error': str(e)}), 500


@bp.route('/flights/<flight_id>', methods=['GET'])
@jwt_required(optional=True)
def get_flight_details_endpoint(flight_id):
    """Get detailed information about a specific flight"""
    try:
        details = get_flight_details(flight_id)
        if not details:
            return jsonify({'msg': 'Flight not found'}), 404
        
        return jsonify(details), 200
    
    except Exception as e:
        print(f"Error fetching flight details: {e}")
        return jsonify({'msg': 'Error fetching flight details', 'error': str(e)}), 500


@bp.route('/flights/status', methods=['GET'])
@jwt_required(optional=True)
def get_flight_status_endpoint():
    """Get flight status using Amadeus"""
    flight_number = request.args.get('flight_number', '').strip()
    date = request.args.get('date', '').strip()
    
    if not flight_number or not date:
        return jsonify({'msg': 'flight_number and date parameters required'}), 400
    
    try:
        status = get_flight_status(flight_number, date)
        if not status:
            return jsonify({'msg': 'Flight status not available'}), 404
        
        return jsonify(status), 200
    
    except Exception as e:
        print(f"Error fetching flight status: {e}")
        return jsonify({'msg': 'Error fetching flight status', 'error': str(e)}), 500


@bp.route('/guides/<destination>', methods=['GET'])
@jwt_required(optional=True)
def get_destination_guide_endpoint(destination):
    try:
        guide = get_destination_guide(destination)
        if not guide:
            return jsonify({'msg': 'Guide not found'}), 404
        
        return jsonify(guide), 200
    
    except Exception as e:
        print(f"Error fetching destination guide: {e}")
        return jsonify({'msg': 'Error fetching destination guide', 'error': str(e)}), 500


@bp.route('/tips/<destination>', methods=['GET'])
@jwt_required(optional=True)
def get_travel_tips_endpoint(destination):
    try:
        tips = get_travel_tips(destination)
        if not tips:
            return jsonify({'msg': 'Tips not found'}), 404
        
        return jsonify(tips), 200
    
    except Exception as e:
        print(f"Error fetching travel tips: {e}")
        return jsonify({'msg': 'Error fetching travel tips', 'error': str(e)}), 500


@bp.route('/flight-destinations', methods=['GET'])
@jwt_required(optional=True)
def search_flight_destinations_endpoint():
    origin = request.args.get('origin', '').strip()
    max_price = request.args.get('max_price', type=float)
    departure_date = request.args.get('departure_date', '').strip() or None
    
    if not origin:
        return jsonify({'msg': 'origin parameter required'}), 400
    
    try:
        destinations = search_flight_destinations(origin, max_price, departure_date)
        return jsonify({
            'destinations': destinations,
            'count': len(destinations)
        }), 200
    except Exception as e:
        print(f"Error searching flight destinations: {e}")
        return jsonify({'msg': 'Error searching flight destinations', 'error': str(e)}), 500


@bp.route('/cheapest-dates', methods=['GET'])
@jwt_required(optional=True)
def search_cheapest_dates_endpoint():
    origin = request.args.get('origin', '').strip()
    destination = request.args.get('destination', '').strip()
    departure_date = request.args.get('departure_date', '').strip() or None
    
    if not origin or not destination:
        return jsonify({'msg': 'origin and destination parameters required'}), 400
    
    try:
        dates = search_cheapest_dates(origin, destination, departure_date)
        return jsonify({
            'dates': dates,
            'count': len(dates)
        }), 200
    except Exception as e:
        print(f"Error searching cheapest dates: {e}")
        return jsonify({'msg': 'Error searching cheapest dates', 'error': str(e)}), 500


@bp.route('/recommended-locations', methods=['GET'])
@jwt_required(optional=True)
def get_recommended_locations_endpoint():
    city_codes = request.args.get('city_codes', '').strip()
    city_list = [c.strip() for c in city_codes.split(',') if c.strip()] if city_codes else None
    
    try:
        locations = get_recommended_locations(city_list)
        return jsonify({
            'locations': locations,
            'count': len(locations)
        }), 200
    except Exception as e:
        print(f"Error getting recommended locations: {e}")
        return jsonify({'msg': 'Error getting recommended locations', 'error': str(e)}), 500


@bp.route('/activities', methods=['GET'])
@jwt_required(optional=True)
def search_activities_endpoint():
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    radius = request.args.get('radius', 5, type=int)
    
    if not lat or not lon:
        return jsonify({'msg': 'lat and lon parameters required'}), 400
    
    try:
        activities = search_activities(lat, lon, radius)
        return jsonify({
            'activities': activities,
            'count': len(activities)
        }), 200
    except Exception as e:
        print(f"Error searching activities: {e}")
        return jsonify({'msg': 'Error searching activities', 'error': str(e)}), 500


@bp.route('/most-traveled', methods=['GET'])
@jwt_required(optional=True)
def get_most_traveled_endpoint():
    origin = request.args.get('origin', '').strip()
    period = request.args.get('period', '2024-01')
    
    if not origin:
        return jsonify({'msg': 'origin parameter required'}), 400
    
    try:
        destinations = get_most_traveled_destinations(origin, period)
        return jsonify({
            'destinations': destinations,
            'count': len(destinations)
        }), 200
    except Exception as e:
        print(f"Error getting most traveled destinations: {e}")
        return jsonify({'msg': 'Error getting most traveled destinations', 'error': str(e)}), 500


@bp.route('/flights/<flight_id>/seatmap', methods=['GET'])
@jwt_required(optional=True)
def get_seatmap_endpoint(flight_id):
    try:
        seatmap = get_seatmap(flight_id)
        if not seatmap:
            return jsonify({'msg': 'Seat map not available'}), 404
        
        return jsonify(seatmap), 200
    except Exception as e:
        print(f"Error fetching seat map: {e}")
        return jsonify({'msg': 'Error fetching seat map', 'error': str(e)}), 500


@bp.route('/flights/price', methods=['POST'])
@jwt_required(optional=True)
def price_flight_offer_endpoint():
    data = request.get_json() or {}
    flight_offer = data.get('flight_offer')
    
    if not flight_offer:
        return jsonify({'msg': 'flight_offer required in request body'}), 400
    
    try:
        priced_offer = price_flight_offer(flight_offer)
        if not priced_offer:
            return jsonify({'msg': 'Failed to price flight offer'}), 400
        
        return jsonify(priced_offer), 200
    except Exception as e:
        print(f"Error pricing flight offer: {e}")
        return jsonify({'msg': 'Error pricing flight offer', 'error': str(e)}), 500

