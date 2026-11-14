import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/routing/ProtectedRoute';
import Unauthorized from './components/routing/Unauthorized';
import { ROLES } from './utils/constants';
import { CartProvider } from './context/CartContext';
import AppShell from './components/common/AppShell';
import { useAuth } from './context/useAuth';
import { LoadingState } from './components/common/Feedback';

import LandingPage from './pages/LandingPage';
import Login from './pages/auth/Login';
import Register from './pages/auth/Register';
import RestaurantList from './pages/customer/RestaurantList';
import RestaurantDetail from './pages/customer/RestaurantDetail';
import Cart from './pages/customer/Cart';
import CustomerDashboard from './pages/customer/CustomerDashboard';
import OwnerDashboard from './pages/owner/OwnerDashboard';
import DeliveryDashboard from './pages/rider/DeliveryDashboard';

const HomeRedirect = () => {
  const { isAuthenticated, loading, user } = useAuth();
  if (loading) return <LoadingState label="Loading your account..." />;
  if (!isAuthenticated) return <LandingPage />;
  const destination = {
    [ROLES.CUSTOMER]: '/restaurants',
    [ROLES.RESTAURANT_OWNER]: '/owner/dashboard',
    [ROLES.DELIVERY_PARTNER]: '/rider/dashboard',
  }[user?.role] || '/unauthorized';
  return <Navigate to={destination} replace />;
};

function App() {
  return (
    <AuthProvider>
      <CartProvider>
        <Router>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/unauthorized" element={<Unauthorized />} />
            <Route path="/" element={<HomeRedirect />} />

            <Route element={<ProtectedRoute allowedRoles={[ROLES.CUSTOMER]} />}>
              <Route element={<AppShell />}>
                <Route path="/restaurants" element={<RestaurantList />} />
                <Route path="/restaurants/:restaurantId" element={<RestaurantDetail />} />
                <Route path="/cart" element={<Cart />} />
                <Route path="/dashboard" element={<CustomerDashboard />} />
              </Route>
            </Route>

            <Route element={<ProtectedRoute allowedRoles={[ROLES.RESTAURANT_OWNER]} />}>
              <Route element={<AppShell />}>
                <Route path="/owner/dashboard" element={<OwnerDashboard />} />
              </Route>
            </Route>

            <Route element={<ProtectedRoute allowedRoles={[ROLES.DELIVERY_PARTNER]} />}>
              <Route element={<AppShell />}>
                <Route path="/rider/dashboard" element={<DeliveryDashboard />} />
              </Route>
            </Route>

            <Route path="*" element={<div className="not-found"><h1>Page not found</h1><a href="/">Return home</a></div>} />
          </Routes>
        </Router>
      </CartProvider>
    </AuthProvider>
  );
}

export default App;