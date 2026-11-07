import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/useAuth';

const ProtectedRoute = ({ allowedRoles = [] }) => {
    const { isAuthenticated, user, loading } = useAuth();
    const location = useLocation();

    if (loading) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
                <p>Loading application...</p>
            </div>
        );
    }

    // Redirect to login if unauthenticated
    if (!isAuthenticated) {
        return <Navigate to="/login" state={{ from: location }} replace />;
    }

    // Normalize roles to lowercase for safe comparison
    const normalizedUserRole = user?.role?.toLowerCase();
    const normalizedAllowedRoles = allowedRoles.map((r) => r.toLowerCase());

    // Check role authorization if restricted roles are defined
    if (normalizedAllowedRoles.length > 0 && !normalizedAllowedRoles.includes(normalizedUserRole)) {
        return <Navigate to="/unauthorized" replace />;
    }

    // Render authorized child route
    return <Outlet />;
};

export default ProtectedRoute;