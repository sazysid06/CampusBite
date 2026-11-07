import { NavLink, Outlet } from 'react-router-dom';
import { useAuth } from '../../context/useAuth';
import { useCart } from '../../context/useCart';

const routeByRole = {
    customer: [
        { to: '/restaurants', label: 'Restaurants' },
        { to: '/dashboard', label: 'My orders & insights' },
    ],
    restaurant_owner: [
        { to: '/owner/dashboard', label: 'Overview' },
    ],
    delivery_partner: [
        { to: '/rider/dashboard', label: 'My deliveries' },
    ],
};

const AppShell = () => {
    const { user, logout } = useAuth();
    const { clearCart, itemCount } = useCart();
    const links = routeByRole[user?.role] || [];

    return (
        <div className="app-frame">
            <header className="topbar">
                <NavLink to={links[0]?.to || '/'} className="brand">
                    <span className="brand-mark">C</span>
                    <span>Campus<span className="brand-accent">Bite</span></span>
                </NavLink>
                <nav className="main-nav" aria-label="Main navigation">
                    {links.map((link) => (
                        <NavLink key={link.to} to={link.to} className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
                            {link.label}
                        </NavLink>
                    ))}
                    {user?.role === 'customer' && (
                        <NavLink to="/cart" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
                            Cart <span className="cart-count">{itemCount}</span>
                        </NavLink>
                    )}
                </nav>
                <div className="account-menu">
                    <span className="account-name">{user?.full_name || user?.email}</span>
                    <button className="button button-quiet button-small" onClick={() => { clearCart(); logout(); }}>Sign out</button>
                </div>
            </header>
            <main className="page-content"><Outlet /></main>
            <footer className="site-footer">
                <span>CampusBite</span>
                <span>Good food, around campus.</span>
            </footer>
        </div>
    );
};

export default AppShell;
