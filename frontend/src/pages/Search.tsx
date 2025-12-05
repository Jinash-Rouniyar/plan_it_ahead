import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';

type SearchType = 'attractions' | 'hotels';

interface SearchResult {
  name?: string;
  title?: string;
  description?: string;
  price?: number;
  price_per_night?: number;
  rating?: number;
  xid?: string;
  hotel_id?: string;
  hotel_key?: string;
  id?: string;
}

interface Itinerary {
  itinerary_id?: number;
  id?: number;
  title?: string;
  start_date?: string;
  end_date?: string;
}

const STORAGE_KEY = 'planit_pending_items';

interface PendingItem {
  type: 'flight' | 'hotel' | 'attraction';
  data: SearchResult;
  addedAt: string;
}

function getPendingItems(): PendingItem[] {
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored ? JSON.parse(stored) : [];
}

function addPendingItem(item: PendingItem): void {
  const items = getPendingItems();
  items.push(item);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
}

function clearPendingItems(): void {
  localStorage.removeItem(STORAGE_KEY);
}

export function Search() {
  const navigate = useNavigate();
  const [searchType, setSearchType] = useState<SearchType>('attractions');
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [attractionDetails, setAttractionDetails] = useState<Record<string, any>>({});
  const [activitiesMap, setActivitiesMap] = useState<Record<string, any[]>>({});
  const [expandedXid, setExpandedXid] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [itineraries, setItineraries] = useState<Itinerary[]>([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [selectedItem, setSelectedItem] = useState<SearchResult | null>(null);
  const [selectedItineraryId, setSelectedItineraryId] = useState<number | null>(null);
  const [dayNumber, setDayNumber] = useState(1);
  const [time, setTime] = useState('10:00');
  const [durationMinutes, setDurationMinutes] = useState(60);
  const [adding, setAdding] = useState(false);
  const [checkIn, setCheckIn] = useState('');
  const [checkOut, setCheckOut] = useState('');
  const [pendingItems, setPendingItems] = useState<PendingItem[]>([]);
  const [currentItinerary, setCurrentItinerary] = useState<{
    itinerary_id: number;
    title: string;
    origin?: string;
    destination?: string;
    departure_date?: string;
    return_date?: string;
  } | null>(null);

  useEffect(() => {
    loadItineraries();
    setPendingItems(getPendingItems());
    
    const storedItinerary = localStorage.getItem('planit_current_itinerary');
    if (storedItinerary) {
      const itinerary = JSON.parse(storedItinerary);
      setCurrentItinerary(itinerary);
      setSelectedItineraryId(itinerary.itinerary_id);
      
      if (itinerary.destination) {
        setQuery(itinerary.destination);
      }
      if (itinerary.departure_date) {
        setCheckIn(itinerary.departure_date);
      }
      if (itinerary.return_date) {
        setCheckOut(itinerary.return_date);
      }
    }
    // If we open the page with attractions selected, trigger a search
    if (searchType === 'attractions') {
      const q = storedItinerary?.destination || query;
      if (q) {
        setQuery(q);
        // small delay to allow state to settle
        setTimeout(() => handleSearch(), 0);
      }
    }
  }, []);

  useEffect(() => {
    // When user switches to attractions, auto-search using currentItinerary.destination if available
    if (searchType === 'attractions') {
      const locationQuery = currentItinerary?.destination || query;
      if (locationQuery) {
        setQuery(locationQuery);
        handleSearch();
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchType]);

  // Helper to switch tabs and clear/refresh results appropriately
  const switchSearchType = (type: SearchType) => {
    // clear existing results and expanded state when switching
    setResults([]);
    setExpandedXid(null);
    setAttractionDetails({});
    setActivitiesMap({});
    setSearchType(type);

    // Auto-search when switching to attractions or when hotels have dates
    setTimeout(() => {
      if (type === 'attractions') {
        const q = currentItinerary?.destination || query;
        if (q) handleSearch('attractions');
      } else if (type === 'hotels') {
        if (checkIn && checkOut && query) handleSearch('hotels');
      }
    }, 0);
  };

  // Helper: detect if an item looks like a hotel response
  const isHotelLike = (item: any) => {
    if (!item) return false;
    return !!(item.hotel_id || item.hotel_key || item.price_per_night || item.rating || item.address);
  };

  // Normalize attraction fields (ensure image_url exists)
  const normalizeAttraction = (item: any) => {
    if (!item) return item;
    const normalized = { ...item };
    normalized.image_url = item.image_url || item.image || item.thumbnail || item.photo || null;
    // keep xid/id mapping consistent
    normalized.xid = item.xid || item.id || item.xid;
    return normalized;
  };

  // Normalize hotel fields (ensure image exists and price_per_night is present)
  const normalizeHotel = (item: any) => {
    if (!item) return item;
    const normalized = { ...item };
    normalized.image = item.image || item.thumbnail || item.image_url || item.photo || null;
    normalized.price_per_night = item.price_per_night || item.price || item.nightly_price || null;
    normalized.hotel_id = item.hotel_id || item.id || item.hotel_key || null;
    return normalized;
  };

  const loadItineraries = async () => {
    try {
      const response = await api.get('/itineraries');
      setItineraries(response.data || []);
    } catch (err) {
      console.error('Failed to load itineraries:', err);
    }
  };

  const handleSearch = async (forceType?: SearchType) => {
    const activeType = forceType || searchType;
    if (!query.trim()) return;

    setLoading(true);
    setError('');
    setSuccessMessage('');
    
    try {
      let response;
      if (activeType === 'attractions') {
        // search attractions by location (city) and also clear any expanded state
        response = await api.get('/search/attractions', { params: { location: query } });
        // Debugging: log response for diagnosis if server returns unexpected shape
        // eslint-disable-next-line no-console
        console.debug('search/attractions response:', response.data);
        // If the attractions endpoint returned an attractions array, normalize/filter it
        if (response.data && response.data.attractions && Array.isArray(response.data.attractions)) {
          const raw = response.data.attractions || [];
          // Normalize each attraction and filter out items that look like hotels
          const normalized = raw.map(normalizeAttraction).filter((it: any) => !isHotelLike(it));
          // Debug: if any items were filtered out, log it
          // eslint-disable-next-line no-console
          console.debug('attractions fetched:', raw.length, 'kept:', normalized.length);

          setResults(normalized);
          setExpandedXid(null);
          setAttractionDetails({});
          setActivitiesMap({});
          if (normalized.length === 0 && raw.length > 0) {
            setError('Attractions endpoint returned results that appear to be hotels; none shown.');
          }
        } else {
          // If the response doesn't include attractions, don't populate with hotels.
          setResults([]);
          // Surface a helpful error so the user knows something unexpected happened
          setError('No attractions found (server returned unexpected data).');
        }
      } else if (activeType === 'hotels') {
        if (!checkIn || !checkOut) {
          setError('Check-in and check-out dates are required');
          setLoading(false);
          return;
        }
        
        response = await api.get('/search/hotels', { 
          params: { 
            location: query,
            check_in: checkIn,
            check_out: checkOut
          } 
        });
        // Debugging: log hotel response
        // eslint-disable-next-line no-console
        console.debug('search/hotels response:', response.data);
        const rawHotels = response.data.hotels || [];
        const normalizedHotels = rawHotels.map(normalizeHotel);
        setResults(normalizedHotels);
      }
    } catch (err) {
      interface ApiError {
        response?: { data?: { msg?: string } };
      }
      const errorResponse = err as ApiError;
      setError(errorResponse.response?.data?.msg || 'Search failed');
    } finally {
      setLoading(false);
    }
  };

  const fetchAttractionDetails = async (xid: string, lat?: number, lon?: number) => {
    if (!xid) return;
    try {
      if (!attractionDetails[xid]) {
        const resp = await api.get(`/search/attractions/${xid}`);
        setAttractionDetails(prev => ({ ...prev, [xid]: resp.data }));
      }

      // fetch nearby activities (ticketed tours) using Amadeus endpoint if coords provided
      const details = attractionDetails[xid] || (await api.get(`/search/attractions/${xid}`)).data;
      const plat = lat || details.lat;
      const plon = lon || details.lon;
      if (plat && plon && !activitiesMap[xid]) {
        const actResp = await api.get('/search/activities', { params: { lat: plat, lon: plon, radius: 10 } });
        setActivitiesMap(prev => ({ ...prev, [xid]: actResp.data.activities || [] }));
      }
    } catch (e) {
      console.error('Failed to load attraction details or activities', e);
    }
  };

  const openAddModal = (item: SearchResult) => {
    setSelectedItem(item);
    setShowAddModal(true);
    setError('');
    if (itineraries.length > 0) {
      const firstItinerary = itineraries[0];
      setSelectedItineraryId(firstItinerary.itinerary_id || firstItinerary.id || null);
    }
  };

  const closeModal = () => {
    setShowAddModal(false);
    setSelectedItem(null);
    setError('');
  };

  const handleAddToLocalStorage = () => {
    if (!selectedItem) return;

    const itemType = searchType === 'hotels' ? 'hotel' : 'attraction';
    
    const pendingItem: PendingItem = {
      type: itemType,
      data: selectedItem,
      addedAt: new Date().toISOString()
    };

    addPendingItem(pendingItem);
    setPendingItems(getPendingItems());
    setSuccessMessage(`${itemType.charAt(0).toUpperCase() + itemType.slice(1)} added to pending items!`);
    closeModal();
  };

  const handleAddToItinerary = async () => {
    if (!selectedItem) {
      setError('No item selected');
      return;
    }

    if (!selectedItineraryId) {
      handleAddToLocalStorage();
      return;
    }

    setAdding(true);
    setError('');

    try {
      const itemType = searchType === 'attractions' ? 'attraction' : 'hotel';
      const itemName = selectedItem.name || selectedItem.title || 'Unknown';
      const estimatedCost = selectedItem.price || selectedItem.price_per_night || 0;

      await api.post(`/itineraries/${selectedItineraryId}/items`, {
        item_type: itemType,
        item_name: itemName,
        estimated_cost: estimatedCost,
        day_number: dayNumber,
        time: searchType === 'attractions' ? time : undefined,
        duration_minutes: searchType === 'attractions' ? durationMinutes : undefined
      });

      // Also add to pending items so it shows up when saving
      handleAddToLocalStorage();
    } catch (err) {
      interface ApiError {
        response?: { data?: { msg?: string } };
      }
      const errorResponse = err as ApiError;
      setError(errorResponse.response?.data?.msg || 'Failed to add item to itinerary');
    } finally {
      setAdding(false);
    }
  };

  const handleSaveAllToItinerary = async () => {
    if (pendingItems.length === 0) {
      setError('No pending items to save');
      return;
    }

    setAdding(true);
    setError('');

    try {
      // Ensure we have an itinerary to save into. If none selected, try to create one.
      let itineraryId = selectedItineraryId as number | null;

      if (!itineraryId) {
        // Try to use the stored current itinerary
        const stored = localStorage.getItem('planit_current_itinerary');
        const storedItinerary = stored ? JSON.parse(stored) : null;

        try {
          let createResp: any = null;
          if (storedItinerary && storedItinerary.departure_date && storedItinerary.return_date) {
            // create using dates and optional title (uses create-from-flights endpoint)
            createResp = await api.post('/itineraries/create-from-flights', {
              departure_date: storedItinerary.departure_date,
              return_date: storedItinerary.return_date,
              title: storedItinerary.title || undefined
            });
          } else {
            // Fallback: create an empty itinerary
            createResp = await api.post('/itineraries', {});
          }

          itineraryId = createResp.data.itinerary_id;

          // Store a minimal current itinerary locally so UX shows the selection
          const title = storedItinerary?.title || `Itinerary ${ (itineraries?.length || 0) + 1 }`;
          const current = {
            itinerary_id: itineraryId,
            title,
            origin: storedItinerary?.origin,
            destination: storedItinerary?.destination,
            departure_date: storedItinerary?.departure_date,
            return_date: storedItinerary?.return_date
          };
          localStorage.setItem('planit_current_itinerary', JSON.stringify(current));
          setCurrentItinerary(current);
          setSelectedItineraryId(itineraryId);
          // reload itineraries list so user can see it in the dropdown
          await loadItineraries();
        } catch (createErr) {
          interface ApiError {
            response?: { data?: { msg?: string } };
          }
          const errorResponse = createErr as ApiError;
          setError(errorResponse.response?.data?.msg || 'Failed to create itinerary');
          setAdding(false);
          return;
        }
      }

      // Prepare payload
      const flights = pendingItems.filter(item => item.type === 'flight').map(item => item.data);
      const items = pendingItems.filter(item => item.type !== 'flight').map(item => ({
        name: item.data.name || item.data.title,
        price: item.data.price || item.data.price_per_night || 0,
        type: item.type
      }));

      // Save to backend
      const response = await api.post(`/itineraries/${itineraryId}/save`, {
        flights,
        items
      });

      localStorage.setItem('planit_saved_data', JSON.stringify({
        itinerary_id: itineraryId,
        ...response.data
      }));

      clearPendingItems();
      setPendingItems([]);
      localStorage.removeItem('planit_current_itinerary');
      setCurrentItinerary(null);
      setSuccessMessage('All items saved to itinerary!');
      navigate(`/itineraries/${itineraryId}`);
    } catch (err) {
      interface ApiError {
        response?: { data?: { msg?: string } };
      }
      const errorResponse = err as ApiError;
      setError(errorResponse.response?.data?.msg || 'Failed to save items');
    } finally {
      setAdding(false);
    }
  };

  const removePendingItem = (index: number) => {
    const items = getPendingItems();
    items.splice(index, 1);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
    setPendingItems(items);
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-6">Search</h1>
      
      {currentItinerary && (
        <div className="mb-6 p-4 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-lg shadow-lg">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-xl font-bold">{currentItinerary.title}</h2>
              <p className="text-sm opacity-90">
                {currentItinerary.origin} → {currentItinerary.destination} | {currentItinerary.departure_date} - {currentItinerary.return_date}
              </p>
              <p className="text-sm mt-1">
                Add hotels and attractions to your trip. Click "Save All to Itinerary" when done.
              </p>
            </div>
            <Button 
              variant="secondary" 
              onClick={() => {
                if (pendingItems.length > 0 && selectedItineraryId) {
                  handleSaveAllToItinerary();
                } else {
                  navigate(`/itineraries/${currentItinerary.itinerary_id}`);
                }
              }}
            >
              {pendingItems.length > 0 ? 'Save & View Itinerary' : 'View Itinerary'}
            </Button>
          </div>
        </div>
      )}
      
      <div className="flex gap-2 mb-6">
        {(['attractions', 'hotels'] as SearchType[]).map((type) => (
          <Button
            key={type}
            variant={searchType === type ? 'default' : 'outline'}
            onClick={() => switchSearchType(type)}
          >
            {type.charAt(0).toUpperCase() + type.slice(1)}
          </Button>
        ))}
      </div>

      <div className="space-y-4 mb-6">
        <div className="flex gap-2">
          <Input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={searchType === 'hotels' ? 'Search location for hotels...' : 'Search for attractions...'}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            className="flex-1"
          />
          <Button onClick={handleSearch} disabled={loading}>
            {loading ? 'Searching...' : 'Search'}
          </Button>
        </div>
        
        {searchType === 'hotels' && (
          <div className="grid grid-cols-2 gap-2">
            <div>
              <Label htmlFor="check_in">Check-in Date</Label>
              <Input
                id="check_in"
                type="date"
                value={checkIn}
                onChange={(e) => setCheckIn(e.target.value)}
                className="mt-1"
              />
            </div>
            <div>
              <Label htmlFor="check_out">Check-out Date</Label>
              <Input
                id="check_out"
                type="date"
                value={checkOut}
                onChange={(e) => setCheckOut(e.target.value)}
                className="mt-1"
              />
            </div>
          </div>
        )}
      </div>

      {pendingItems.length > 0 && (
        <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <h3 className="font-bold mb-2">Pending Items ({pendingItems.length})</h3>
          <div className="space-y-2">
            {pendingItems.map((item, index) => (
              <div key={index} className="flex justify-between items-center bg-white p-2 rounded">
                <span>
                  <strong>{item.type}:</strong> {item.data.name || item.data.title} 
                  {(item.data.price || item.data.price_per_night) && ` - $${item.data.price || item.data.price_per_night}`}
                </span>
                <Button variant="outline" size="sm" onClick={() => removePendingItem(index)}>
                  Remove
                </Button>
              </div>
            ))}
          </div>
          <div className="mt-4 flex gap-2">
            <select
              value={selectedItineraryId || ''}
              onChange={(e) => setSelectedItineraryId(e.target.value ? parseInt(e.target.value) : null)}
              className="flex-1 px-3 py-2 border rounded-md"
            >
              <option value="">Select Itinerary</option>
              {itineraries.map((it) => (
                <option key={it.itinerary_id || it.id} value={it.itinerary_id || it.id}>
                  {it.title || `Itinerary ${it.itinerary_id || it.id}`}
                </option>
              ))}
            </select>
            <Button onClick={handleSaveAllToItinerary} disabled={adding || !selectedItineraryId}>
              {adding ? 'Saving...' : 'Save All to Itinerary'}
            </Button>
            <Button variant="outline" onClick={() => { clearPendingItems(); setPendingItems([]); }}>
              Clear All
            </Button>
          </div>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      {successMessage && (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded mb-4">
          {successMessage}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {results.map((item, index) => {
          if (searchType === 'hotels') {
            // Render hotel card
            const hotelId = (item as any).hotel_id || (item as any).hotel_key || (item as any).id || '';
            return (
              <Card key={index} className={`hover:shadow-lg transition`}>
                <div>
                  <CardHeader>
                    <CardTitle className="text-lg">{item.name || item.title || 'Unknown Hotel'}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    { (item as any).image && (
                      <img src={(item as any).image} alt={item.name} className={`w-full object-cover rounded mb-2 h-36`} />
                    ) }
                    {item.price_per_night && <p className="text-green-600 font-bold mb-1">${item.price_per_night} / night</p>}
                    {item.rating && <p className="text-sm mb-1">Rating: {item.rating}</p>}
                    { (item as any).address && <p className="text-sm text-gray-600 mb-2">{(item as any).address}</p> }
                    <div className="flex gap-2">
                      <Button onClick={() => openAddModal(item)} className="flex-1">Add to Itinerary</Button>
                    </div>
                  </CardContent>
                </div>
              </Card>
            );
          }

          // Default: attractions rendering (existing behavior)
          const xid = (item as any).xid || (item as any).id || '';
          const isExpanded = expandedXid === xid;
          const details = xid ? attractionDetails[xid] : null;
          const activities = xid ? activitiesMap[xid] : [];

          return (
            <Card key={index} className={`hover:shadow-lg transition ${isExpanded ? 'ring-2 ring-indigo-300' : ''}`}>
              <div onClick={async () => {
                // toggle expansion; if expanding, fetch details
                if (isExpanded) {
                  setExpandedXid(null);
                } else {
                  setExpandedXid(xid);
                  if (xid) await fetchAttractionDetails(xid, (item as any).lat, (item as any).lon);
                }
              }} style={{ cursor: xid ? 'pointer' : 'default' }}>
                <CardHeader>
                  <CardTitle className="text-lg">{item.name || item.title || 'Unknown'}</CardTitle>
                </CardHeader>
                <CardContent>
                  { (item as any).image_url && (
                    <img src={(item as any).image_url} alt={item.name} className={`w-full object-cover rounded mb-2 ${isExpanded ? 'h-64' : 'h-36'}`} />
                  ) }

                  {isExpanded ? (
                    <>
                      <p className="text-sm text-gray-700 mb-2">{(details && details.description) || item.description || 'No description available.'}</p>
                      {activities && activities.length > 0 && (
                        <div className="mb-2">
                          <h4 className="font-semibold">Nearby tours & ticketed activities</h4>
                          <div className="space-y-2 mt-2">
                            {activities.map((a, i) => (
                              <div key={i} className="p-2 bg-white border rounded flex justify-between items-center">
                                <div>
                                  <div className="font-medium">{a.name}</div>
                                  {a.description && <div className="text-sm text-gray-600">{a.description.substring(0,100)}...</div>}
                                  {a.price ? <div className="text-sm text-green-600">{a.currency || 'USD'} ${a.price}</div> : null}
                                </div>
                                <div className="flex flex-col gap-2">
                                  {a.bookingLink && (
                                    <a className="text-sm text-blue-600 underline" href={a.bookingLink} target="_blank" rel="noreferrer">Book</a>
                                  )}
                                  <Button size="sm" onClick={() => { openAddModal({ name: a.name, title: a.name, description: a.description, price: a.price }); }}>Add</Button>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      <div className="flex gap-2 mt-3">
                        <Button onClick={() => openAddModal({ xid, name: item.name, title: item.name, description: details?.description || item.description, price: item.rate })} className="flex-1">Add to Itinerary</Button>
                        <Button variant="outline" onClick={() => { setExpandedXid(null); }}>Close</Button>
                      </div>
                    </>
                  ) : (
                    <>
                      {item.description && (<p className="text-sm text-gray-600 mb-2">{item.description.substring(0, 100)}...</p>)}
                      {item.rate && <p className="text-sm mb-2">Popularity: {item.rate}</p>}
                      <Button onClick={() => openAddModal(item)} className="w-full" size="sm">Add to Itinerary</Button>
                    </>
                  )}
                </CardContent>
              </div>
            </Card>
          );
        })}
      </div>

      {results.length === 0 && !loading && query && (
        <p className="text-center text-gray-500 mt-8">No results found</p>
      )}

      {showAddModal && selectedItem && (
        <div 
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
          onClick={(e) => {
            if (e.target === e.currentTarget) closeModal();
          }}
        >
          <Card className="w-full max-w-md mx-4 bg-white">
            <CardHeader>
              <CardTitle>Add to Itinerary</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>Item</Label>
                <p className="font-medium">{selectedItem.name || selectedItem.title}</p>
                {(selectedItem.price || selectedItem.price_per_night) && (
                  <p className="text-green-600 font-bold">${selectedItem.price || selectedItem.price_per_night}</p>
                )}
              </div>

              {itineraries.length > 0 ? (
                <div>
                  <Label htmlFor="itinerary">Select Itinerary (optional)</Label>
                  <select
                    id="itinerary"
                    value={selectedItineraryId || ''}
                    onChange={(e) => setSelectedItineraryId(e.target.value ? parseInt(e.target.value) : null)}
                    className="w-full px-3 py-2 border rounded-md mt-1"
                  >
                    <option value="">-- Add to pending items --</option>
                    {itineraries.map((it) => (
                      <option key={it.itinerary_id || it.id} value={it.itinerary_id || it.id}>
                        {it.title || `Itinerary ${it.itinerary_id || it.id}`}
                      </option>
                    ))}
                  </select>
                </div>
              ) : (
                <p className="text-gray-500 text-sm">
                  No itineraries found. Item will be added to pending items.
                </p>
              )}

              {searchType === 'attractions' && selectedItineraryId && (
                <>
                  <div>
                    <Label htmlFor="day">Day Number</Label>
                    <Input
                      id="day"
                      type="number"
                      min="1"
                      value={dayNumber}
                      onChange={(e) => setDayNumber(parseInt(e.target.value) || 1)}
                      className="mt-1"
                    />
                  </div>

                  <div>
                    <Label htmlFor="time">Start Time (HH:MM)</Label>
                    <Input
                      id="time"
                      type="time"
                      value={time}
                      onChange={(e) => setTime(e.target.value)}
                      className="mt-1"
                    />
                  </div>

                  <div>
                    <Label htmlFor="duration">Duration (minutes)</Label>
                    <Input
                      id="duration"
                      type="number"
                      min="15"
                      step="15"
                      value={durationMinutes}
                      onChange={(e) => setDurationMinutes(parseInt(e.target.value) || 60)}
                      className="mt-1"
                    />
                  </div>
                </>
              )}

              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
                  {error}
                </div>
              )}

              <div className="flex gap-2">
                <Button
                  onClick={handleAddToItinerary}
                  disabled={adding}
                  className="flex-1"
                >
                  {adding ? 'Adding...' : (selectedItineraryId ? 'Add to Itinerary' : 'Add to Pending')}
                </Button>
                <Button
                  variant="outline"
                  onClick={closeModal}
                  className="flex-1"
                >
                  Cancel
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
