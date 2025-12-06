import { Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuthHook';
import { Button } from '../components/ui/button';

export function Home() {
  const { user } = useAuth();

  return (
    <div className="relative min-h-screen overflow-hidden bg-gray-50">
      {/* Video background - place a file at `public/videos/beach.mp4` or update the src below */}
      <video className="absolute inset-0 w-full h-full object-cover" autoPlay muted loop playsInline>
        <source src="/videos/beach.mp4" type="video/mp4" />
        {/* If you prefer an external URL, replace the src above with the URL. */}
      </video>
      {/* slight dark overlay to keep text readable */}
      <div className="absolute inset-0 bg-black/30" />

      <div className="relative container mx-auto px-4 py-16">
        <div className="text-center mb-6">
          <h1 className="text-5xl font-bold mb-4 text-white">Plan It Ahead</h1>
          <p className="text-lg text-white/90">Your AI-powered travel planning companion</p>
        </div>

        <div className="h-[60vh] flex items-center justify-center">
          <div className="w-full flex items-center justify-center">
            {user ? (
              <div className="flex flex-col md:flex-row items-center justify-center gap-6">
                <Link to="/itineraries/create" className="w-full md:w-auto">
                  <Button size="lg" className="px-14 py-5 text-2xl text-black bg-transparent hover:text-primary hover:bg-transparent">Start Planning</Button>
                </Link>
                <Link to="/ai" className="w-full md:w-auto">
                  <Button
                    size="lg"
                    variant="outline"
                    className="px-14 py-5 text-2xl border-0 bg-transparent text-black hover:text-primary hover:bg-transparent"
                  >
                    AI Itinerary Generator
                  </Button>
                </Link>
              </div>
            ) : (
              <div className="flex flex-col md:flex-row items-center justify-center gap-6">
                <Link to="/register" className="w-full md:w-auto">
                  <Button size="lg" className="px-14 py-5 text-2xl text-black bg-transparent hover:text-primary hover:bg-transparent">Get Started</Button>
                </Link>
                <Link to="/login" className="w-full md:w-auto">
                  <Button
                    size="lg"
                    variant="outline"
                    className="px-14 py-5 text-2xl border-0 bg-transparent text-black hover:text-primary hover:bg-transparent"
                  >
                    Login
                  </Button>
                </Link>
              </div>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mt-32 opacity-60 text-sm text-white">
          <div className="text-center p-4">
            <h2 className="text-xl font-medium mb-1">AI-Powered Planning</h2>
            <p className="text-white/90">
              Personalized itineraries optimized for your preferences, budget, and time
            </p>
          </div>

          <div className="text-center p-4">
            <h2 className="text-xl font-medium mb-1">Find Companions</h2>
            <p className="text-white/90">
              Connect with travelers planning similar trips and share your journey
            </p>
          </div>

          <div className="text-center p-4">
            <h2 className="text-xl font-medium mb-1">All-in-One Platform</h2>
            <p className="text-white/90">
              Search destinations, attractions, hotels, and flights in one place
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

