import { useCallback, useEffect, useState } from 'react';
import { EmptyState, ErrorMessage, LoadingState } from '../../components/common/Feedback';
import OrderCard from '../../components/common/OrderCard';
import { useAuth } from '../../context/useAuth';
import { orderService } from '../../services/orderService';
import { restaurantService } from '../../services/restaurantService';
import { formatMoney, formatStatus, getErrorMessage } from '../../utils/formatters';

const OwnerDashboard = () => {
    const { user } = useAuth();
    const [restaurant, setRestaurant] = useState(null);
    const [orders, setOrders] = useState([]);
    const [analytics, setAnalytics] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [notice, setNotice] = useState('');
    const [restaurantForm, setRestaurantForm] = useState({ name: '', description: '', address: '', phone_number: '' });
    const [menuForm, setMenuForm] = useState({ name: '', description: '', price: '', category: '' });
    const [savingRestaurant, setSavingRestaurant] = useState(false);
    const [savingMenuItem, setSavingMenuItem] = useState(false);
    const [resolvingRefund, setResolvingRefund] = useState(null);

    const loadData = useCallback(async () => {
        setError('');
        const [restaurantResult, orderResult, analyticsResult] = await Promise.allSettled([
            restaurantService.list(),
            orderService.listMine(),
            orderService.restaurantAnalytics(),
        ]);
        if (restaurantResult.status === 'fulfilled') {
            const mine = restaurantResult.value.find((entry) => entry.owner_id === user.id) || null;
            if (mine) {
                try {
                    setRestaurant(await restaurantService.get(mine.id));
                } catch (requestError) {
                    setRestaurant(mine);
                    setError(getErrorMessage(requestError, 'Could not load your menu.'));
                }
            } else {
                setRestaurant(null);
            }
        } else {
            setError(getErrorMessage(restaurantResult.reason, 'Could not load your restaurant.'));
        }
        if (orderResult.status === 'fulfilled') setOrders(orderResult.value);
        else setError((current) => current || getErrorMessage(orderResult.reason, 'Could not load orders.'));
        if (analyticsResult.status === 'fulfilled') setAnalytics(analyticsResult.value);
        else if (analyticsResult.reason.response?.status !== 404) {
            setError((current) => current || getErrorMessage(analyticsResult.reason, 'Could not load analytics.'));
        }
        setLoading(false);
    }, [user.id]);

    useEffect(() => {
        const timer = window.setTimeout(loadData, 0);
        return () => window.clearTimeout(timer);
    }, [loadData]);

    const createRestaurant = async (event) => {
        event.preventDefault();
        setSavingRestaurant(true);
        setError('');
        try {
            await restaurantService.create({ ...restaurantForm, is_open: true });
            setNotice('Your restaurant is live. Add your first menu item below.');
            setRestaurantForm({ name: '', description: '', address: '', phone_number: '' });
            setLoading(true);
            await loadData();
        } catch (requestError) {
            setError(getErrorMessage(requestError, 'Could not create your restaurant.'));
        } finally {
            setSavingRestaurant(false);
        }
    };

    const addMenuItem = async (event) => {
        event.preventDefault();
        setSavingMenuItem(true);
        setError('');
        try {
            await restaurantService.addMenuItem(restaurant.id, {
                ...menuForm,
                price: Number(menuForm.price),
                is_available: true,
            });
            setNotice('Menu item added.');
            setMenuForm({ name: '', description: '', price: '', category: '' });
            await loadData();
        } catch (requestError) {
            setError(getErrorMessage(requestError, 'Could not add this menu item.'));
        } finally {
            setSavingMenuItem(false);
        }
    };

    const updateOrder = async (orderId, status) => {
        setError('');
        try {
            await orderService.updateStatus(orderId, status);
            setNotice(`Order #${orderId} updated.`);
            setLoading(true);
            await loadData();
        } catch (requestError) {
            setError(getErrorMessage(requestError, 'Could not update this order.'));
        }
    };

    const decideRefund = async (orderId, decision) => {
        setError('');
        setNotice('');
        setResolvingRefund(orderId);
        try {
            await orderService.decideRefund(orderId, decision);
            setNotice(`Refund request for order #${orderId} ${decision}.`);
            await loadData();
        } catch (requestError) {
            setError(getErrorMessage(requestError, 'Could not resolve this refund request.'));
        } finally {
            setResolvingRefund(null);
        }
    };

    if (loading) return <LoadingState label="Loading your restaurant dashboard..." />;

    if (!restaurant) {
        return (
            <div className="content-stack narrow-content">
                <div className="page-heading"><span className="eyebrow">OWNER SETUP</span><h1>Bring your kitchen online.</h1><p>Create your restaurant profile to start managing menus and orders.</p></div>
                <ErrorMessage message={error} />
                <section className="panel"><h2>Restaurant details</h2>
                    <form className="form-grid" onSubmit={createRestaurant}>
                        <label className="field">Restaurant name<input required minLength={2} maxLength={150} value={restaurantForm.name} onChange={(e) => setRestaurantForm({ ...restaurantForm, name: e.target.value })} /></label>
                        <label className="field">Phone number<input required minLength={10} maxLength={20} value={restaurantForm.phone_number} onChange={(e) => setRestaurantForm({ ...restaurantForm, phone_number: e.target.value })} /></label>
                        <label className="field field-wide">Address<input required minLength={5} maxLength={255} value={restaurantForm.address} onChange={(e) => setRestaurantForm({ ...restaurantForm, address: e.target.value })} /></label>
                        <label className="field field-wide">Description<textarea rows="3" value={restaurantForm.description} onChange={(e) => setRestaurantForm({ ...restaurantForm, description: e.target.value })} /></label>
                        <button className="button button-primary field-wide" disabled={savingRestaurant}>{savingRestaurant ? 'Creating...' : 'Create restaurant'}</button>
                    </form>
                </section>
            </div>
        );
    }

    const nextStatus = { placed: 'accepted', accepted: 'preparing', preparing: 'ready' };

    return (
        <div className="content-stack">
            <section className="page-heading"><span className="eyebrow">OWNER DASHBOARD</span><h1>{restaurant.name}</h1><p>Manage your menu and keep today's orders moving.</p></section>
            {notice && <div className="notice notice-success" role="status">{notice}</div>}
            <ErrorMessage message={error} />
            {analytics && <section className="stats-grid">
                <div className="stat-card"><span>TOTAL ORDERS</span><strong>{analytics.total_orders}</strong><small>{analytics.completed_orders} delivered</small></div>
                <div className="stat-card"><span>DELIVERED REVENUE</span><strong>{formatMoney(analytics.total_revenue)}</strong><small>Based on completed orders</small></div>
                <div className="stat-card"><span>CANCELLED / REFUNDED</span><strong>{analytics.cancelled_orders} / {analytics.refunded_orders}</strong><small>Order counts</small></div>
            </section>}
            <div className="dashboard-columns">
                <section className="section-block">
                    <div className="section-heading"><div><span className="eyebrow">KITCHEN QUEUE</span><h2>Incoming orders</h2></div></div>
                    {orders.length ? <div className="order-list">{orders.map((order) => (
                        <OrderCard key={order.id} order={order} restaurantName={restaurant.name}>
                            {nextStatus[order.status] && <button className="button button-primary button-small" onClick={() => updateOrder(order.id, nextStatus[order.status])}>Mark {formatStatus(nextStatus[order.status])}</button>}
                            {['placed', 'accepted'].includes(order.status) && <button className="button button-danger button-small" onClick={() => updateOrder(order.id, 'cancelled')}>Cancel</button>}
                            {order.delivery?.delivery_partner_id && <span className="muted-note">Rider #{order.delivery.delivery_partner_id} · {formatStatus(order.delivery.status)}</span>}
                            {['accepted', 'preparing', 'ready'].includes(order.status) && !order.delivery?.delivery_partner_id && <span className="muted-note">Waiting for an available rider. The system will assign one automatically.</span>}
                            {order.refund_request && (
                                <>
                                    <span className="muted-note">
                                        Refund {order.refund_request.status}: {order.refund_request.reason}
                                    </span>
                                    {order.refund_request.status === 'pending' && (
                                        <>
                                            <button
                                                className="button button-primary button-small"
                                                disabled={resolvingRefund === order.id}
                                                onClick={() => decideRefund(order.id, 'approved')}
                                            >
                                                Approve refund
                                            </button>
                                            <button
                                                className="button button-danger button-small"
                                                disabled={resolvingRefund === order.id}
                                                onClick={() => decideRefund(order.id, 'rejected')}
                                            >
                                                Reject refund
                                            </button>
                                        </>
                                    )}
                                    {order.refund_request.decision_notes && (
                                        <span className="muted-note">{order.refund_request.decision_notes}</span>
                                    )}
                                </>
                            )}
                        </OrderCard>
                    ))}</div> : <EmptyState title="No orders yet" detail="New customer orders will show up here." />}
                </section>
                <section className="section-block">
                    <div className="section-heading"><div><span className="eyebrow">YOUR OFFERING</span><h2>Menu items</h2></div></div>
                    <div className="panel menu-manager">
                        {restaurant.menu_items?.length ? restaurant.menu_items.map((item) => (
                            <div className="menu-manager-row" key={item.id}><div><strong>{item.name}</strong><small>{item.category} · {item.is_available ? 'Available' : 'Unavailable'}</small></div><strong>{formatMoney(item.price)}</strong></div>
                        )) : <p className="muted-note">Your menu is empty. Add your first item below.</p>}
                    </div>
                    <div className="panel"><h3>Add menu item</h3>
                        <form className="form-grid" onSubmit={addMenuItem}>
                            <label className="field field-wide">Item name<input required minLength={2} maxLength={120} value={menuForm.name} onChange={(e) => setMenuForm({ ...menuForm, name: e.target.value })} /></label>
                            <label className="field">Category<input required minLength={2} maxLength={50} value={menuForm.category} onChange={(e) => setMenuForm({ ...menuForm, category: e.target.value })} placeholder="Main course, drink..." /></label>
                            <label className="field">Price (₹)<input type="number" required min="0.01" step="0.01" value={menuForm.price} onChange={(e) => setMenuForm({ ...menuForm, price: e.target.value })} /></label>
                            <label className="field field-wide">Description<textarea rows="2" value={menuForm.description} onChange={(e) => setMenuForm({ ...menuForm, description: e.target.value })} /></label>
                            <button className="button button-primary field-wide" disabled={savingMenuItem}>{savingMenuItem ? 'Adding...' : 'Add to menu'}</button>
                        </form>
                    </div>
                </section>
            </div>
        </div>
    );
};

export default OwnerDashboard;
