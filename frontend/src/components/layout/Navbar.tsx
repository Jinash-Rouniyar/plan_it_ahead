import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuthHook';
import { Button } from '../ui/button';

export function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isActive = (path: string) => {
    return location.pathname === path || location.pathname.startsWith(path + '/');
  };

  return (
    <nav className="border-b border-indigo-100 bg-gradient-to-r from-blue-50 via-indigo-50 to-purple-50 shadow-sm">
      <div className="container mx-auto px-4 py-3 flex items-center justify-between">
        <Link to="/" className="text-2xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
          Plan It Ahead
        </Link>
        
        <div className="flex items-center gap-4">
          {user ? (
            <>
              <Link 
                to="/itineraries" 
                className={`text-sm font-medium transition-colors ${
                  isActive('/itineraries') 
                    ? 'text-indigo-600' 
                    : 'text-gray-700 hover:text-indigo-600'
                }`}
              >
                My Itineraries
              </Link>
              <Link 
                to="/ai" 
                className={`text-sm font-medium transition-colors ${
                  isActive('/ai') 
                    ? 'text-indigo-600' 
                    : 'text-gray-700 hover:text-indigo-600'
                }`}
              >
                AI Planner
              </Link>
              <Link 
                to="/companions" 
                className={`text-sm font-medium transition-colors ${
                  isActive('/companions') 
                    ? 'text-indigo-600' 
                    : 'text-gray-700 hover:text-indigo-600'
                }`}
              >
                Companions
              </Link>
              <Link 
                to="/chat" 
                className={`text-sm font-medium transition-colors ${
                  isActive('/chat') 
                    ? 'text-indigo-600' 
                    : 'text-gray-700 hover:text-indigo-600'
                }`}
              >
                Chat
              </Link>
              <span className="text-sm text-indigo-600 font-medium">{user.name}</span>
              <Button variant="outline" size="sm" onClick={handleLogout} className="border-indigo-200 text-indigo-600 hover:bg-indigo-50">
                Logout
              </Button>
            </>
          ) : (
            <>
              <Link to="/login">
                <Button variant="ghost" size="sm" className="text-gray-700 hover:text-indigo-600 hover:bg-indigo-50">Login</Button>
              </Link>
              <Link to="/register">
                <Button size="sm" className="bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white">Sign Up</Button>
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}

