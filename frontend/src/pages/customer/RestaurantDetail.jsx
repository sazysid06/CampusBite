import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { EmptyState, ErrorMessage, LoadingState } from '../../components/common/Feedback';
import { useCart } from '../../context/useCart';
import { restaurantService } from '../../services/restaurantService';
import { formatMoney, getErrorMessage } from '../../utils/formatters';

const RestaurantDetail = () => {
    const { restaurantId } = useParams();
    const navigate = useNavigate();
    const { addItem, itemCount } = useCart();
    const [result, setResult] = useState({ restaurantId: null, restaurant: null, loading: true, error: '' });
    const { restaurant, loading, error } = result;
    const [cartNotice, setCartNotice] = useState('');

    useEffect(() => {
        let isMounted = true;
        const timer = window.setTimeout(() => {
            restaurantService.get(restaurantId)
                .then((data) => {
                    if (isMounted) setResult({ restaurantId, restaurant: data, loading: false, error: '' });
                })
                .catch((requestError) => {
                    if (isMounted) setResult({
                        restaurantId,
                        restaurant: null,
                        loading: false,
                        error: getErrorMessage(requestError, 'Could not load this menu.'),
                    });
                });
        }, 0);
        return () => {
            isMounted = false;
            window.clearTimeout(timer);
        };
    }, [restaurantId]);

    const handleAdd = (item) => {
        const added = addItem(restaurant, item);
        setCartNotice(added ? `${item.name} added to your cart.` : 'Your cart has items from another restaurant. Clear it before switching restaurants.');
    };

    if (loading || result.restaurantId !== restaurantId) return <LoadingState label="Loading the menu..." />;
    if (error) return <ErrorMessage message={error} />;
    if (!restaurant) return <EmptyState title="Restaurant not found" detail="It may have been removed or is temporarily unavailable." />;

    return (
        <div className="content-stack">
            <Link to="/restaurants" className="back-link">← All restaurants</Link>
            <section className="detail-hero">
                <div className="detail-avatar">{restaurant.name.slice(0, 1).toUpperCase()}</div>
                <div><span className="eyebrow">{restaurant.is_open ? 'OPEN FOR ORDERS' : 'CURRENTLY CLOSED'}</span><h1>{restaurant.name}</h1><p>{restaurant.description || 'A campus kitchen serving up something good.'}</p><span className="restaurant-address">{restaurant.address} · {restaurant.phone_number}</span></div>
                {itemCount > 0 && <button className="button button-primary" onClick={() => navigate('/cart')}>View cart ({itemCount})</button>}
            </section>
            {cartNotice && <div className="notice notice-info" role="status">{cartNotice}</div>}
            <section className="section-block">
                <div className="section-heading"><div><span className="eyebrow">FRESH FROM THE KITCHEN</span><h2>Menu</h2></div></div>
                {restaurant.menu_items?.length ? (
                    <div className="menu-list">
                        {restaurant.menu_items.map((item) => (
                            <article className="menu-item" key={item.id}>
                                <div className="menu-item-icon">{item.name.slice(0, 1).toUpperCase()}</div>
                                <div className="menu-item-copy"><span className="eyebrow">{item.category}</span><h3>{item.name}</h3><p>{item.description || 'Prepared fresh when you order.'}</p></div>
                                <div className="menu-item-action"><strong>{formatMoney(item.price)}</strong><button className="button button-primary button-small" disabled={!item.is_available || !restaurant.is_open} onClick={() => handleAdd(item)}>{item.is_available ? 'Add +' : 'Unavailable'}</button></div>
                            </article>
                        ))}
                    </div>
                ) : <EmptyState title="The menu is on its way" detail="This restaurant has not added any items yet." />}
            </section>
        </div>
    );
};

export default RestaurantDetail;
