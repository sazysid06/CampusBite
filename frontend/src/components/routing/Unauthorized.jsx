import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/useAuth';

const Unauthorized = () => {
    const navigate = useNavigate();
    const { user } = useAuth();

    const handleReturn = () => {
        const role = user?.role?.toLowerCase();
        if (role === 'restaurant_owner') {
            navigate('/owner/dashboard');
        } else if (role === 'delivery_partner') {
            navigate('/rider/dashboard');
        } else {
            navigate('/restaurants');
        }
    };

    return (
        <div style={{ padding: '2rem', textAlign: 'center', marginTop: '4rem' }}>
            <h1>403 - Access Denied</h1>
            <p>You do not have permission to view this page with your current role.</p>
            <button
                onClick={handleReturn}
                style={{ padding: '0.6rem 1.2rem', marginTop: '1rem', cursor: 'pointer' }}
            >
                Go to Your Dashboard
            </button>
        </div>
    );
};

export default Unauthorized;