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
  }, []);

  const loadItineraries = async () => {
    try {
      const response = await api.get('/itineraries');
      setItineraries(response.data || []);
    } catch (err) {
      console.error('Failed to load itineraries:', err);
    }
  };

  const handleSearch = async () => {
    if (!query.trim()) return;

    setLoading(true);
    setError('');
    setSuccessMessage('');
    
    try {
      let response;
      if (searchType === 'attractions') {
        response = await api.get('/search/attractions', { params: { location: query } });
        setResults(response.data.attractions || []);
      } else if (searchType === 'hotels') {
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
        setResults(response.data.hotels || []);
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

    if (!selectedItineraryId) {
      setError('Please select an itinerary first');
      return;
    }

    setAdding(true);
    setError('');

    try {
      const flights = pendingItems.filter(item => item.type === 'flight').map(item => item.data);
      const items = pendingItems.filter(item => item.type !== 'flight').map(item => ({
        name: item.data.name || item.data.title,
        price: item.data.price || item.data.price_per_night || 0,
        type: item.type
      }));

      const response = await api.post(`/itineraries/${selectedItineraryId}/save`, {
        flights,
        items
      });

      localStorage.setItem('planit_saved_data', JSON.stringify({
        itinerary_id: selectedItineraryId,
        ...response.data
      }));

      clearPendingItems();
      setPendingItems([]);
      localStorage.removeItem('planit_current_itinerary');
      setCurrentItinerary(null);
      setSuccessMessage('All items saved to itinerary!');
      navigate(`/itineraries/${selectedItineraryId}`);
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
            onClick={() => setSearchType(type)}
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
              onChange={(e) => setSelectedItineraryId(parseInt(e.target.value))}
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
        {results.map((item, index) => (
          <Card key={index} className="hover:shadow-lg transition">
            <CardHeader>
              <CardTitle className="text-lg">
                {item.name || item.title || 'Unknown'}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {item.description && (
                <p className="text-sm text-gray-600 mb-2">{item.description.substring(0, 100)}...</p>
              )}
              {item.price && <p className="text-lg font-bold mb-2">${item.price}</p>}
              {item.price_per_night && <p className="text-lg font-bold mb-2">${item.price_per_night}/night</p>}
              {item.rating && <p className="text-sm mb-4">Rating: {item.rating}</p>}
              <Button
                onClick={() => openAddModal(item)}
                className="w-full"
                size="sm"
              >
                Add to Itinerary
              </Button>
            </CardContent>
          </Card>
        ))}
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
