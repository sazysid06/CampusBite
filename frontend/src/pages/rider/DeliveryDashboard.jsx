import { useCallback, useEffect, useState } from 'react';
import { EmptyState, ErrorMessage, LoadingState } from '../../components/common/Feedback';
import OrderCard from '../../components/common/OrderCard';
import { orderService } from '../../services/orderService';
import { formatStatus, getErrorMessage } from '../../utils/formatters';

const DeliveryDashboard = () => {
    const [orders, setOrders] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [notice, setNotice] = useState('');
    const [available, setAvailable] = useState(false);
    const [savingAvailability, setSavingAvailability] = useState(false);

    const loadOrders = useCallback(async () => {
        setError('');
        try {
            const [myOrders, riderAvailability] = await Promise.all([
                orderService.listMine(),
                orderService.getRiderAvailability(),
            ]);
            setOrders(myOrders);
            setAvailable(riderAvailability.is_available);
        } catch (requestError) {
            setError(getErrorMessage(requestError, 'Could not load your delivery tracker.'));
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        const timer = window.setTimeout(loadOrders, 0);
        return () => window.clearTimeout(timer);
    }, [loadOrders]);

    const updateDelivery = async (order, status) => {
        setError('');
        try {
            await orderService.updateDeliveryStatus(order.id, status);
            setNotice(`Order #${order.id}: ${formatStatus(status).toLowerCase()}.`);
            setLoading(true);
            await loadOrders();
        } catch (requestError) {
            setError(getErrorMessage(requestError, 'Could not update your delivery tracker.'));
        }
    };

    const changeAvailability = async (nextAvailability) => {
        setError('');
        setSavingAvailability(true);
        try {
            const result = await orderService.setRiderAvailability(nextAvailability);
            setAvailable(result.is_available);
            setNotice(result.is_available
                ? 'You are available for deliveries.'
                : nextAvailability
                    ? 'A waiting delivery has been assigned to you.'
                    : 'You are now offline.');
            await loadOrders();
        } catch (requestError) {
            setError(getErrorMessage(requestError, 'Could not update your availability.'));
        } finally {
            setSavingAvailability(false);
        }
    };

    if (loading) return <LoadingState label="Checking your assigned deliveries..." />;

    const activeOrders = orders.filter((order) => (
        ['accepted', 'preparing', 'ready', 'assigned', 'out_for_delivery'].includes(order.status)
    ));

    const nextDeliveryStatus = (order) => {
        if (['on_the_way_to_restaurant', 'assigned'].includes(order.delivery?.status)) {
            return { status: 'at_restaurant', label: 'Arrived at restaurant' };
        }
        if (order.delivery?.status === 'at_restaurant' && order.status === 'ready') {
            return { status: 'picked_up', label: 'Confirm pickup' };
        }
        if (order.delivery?.status === 'picked_up') {
            return { status: 'on_route', label: 'Start delivery' };
        }
        return null;
    };

    return (
        <div className="content-stack">
            <section className="page-heading"><span className="eyebrow">DELIVERY PARTNER</span><h1>Every delivery matters.</h1><p>Your assigned campus orders, all in one place.</p></section>
            {notice && <div className="notice notice-success" role="status">{notice}</div>}
            <ErrorMessage message={error} />
            <section className="panel rider-availability">
                <div>
                    <span className="eyebrow">RIDER TRACKER</span>
                    <h2>{available ? 'Available' : activeOrders.length ? 'On a delivery' : 'Offline'}</h2>
                    <p>{available ? 'You can receive a new delivery assignment.' : 'Turn availability on when you are ready to accept deliveries.'}</p>
                </div>
                <div className="availability-actions">
                    {available && <button className="button button-quiet" disabled={savingAvailability} onClick={() => changeAvailability(true)}>Check for waiting orders</button>}
                    <button className={available ? 'button button-danger' : 'button button-primary'} disabled={savingAvailability || (!available && activeOrders.length > 0)} onClick={() => changeAvailability(!available)}>
                        {savingAvailability ? 'Updating...' : available ? 'Go offline' : 'Go available'}
                    </button>
                </div>
            </section>
            <section className="section-block">
                <div className="section-heading"><div><span className="eyebrow">YOUR ROUTE</span><h2>Active deliveries <span className="count-bubble">{activeOrders.length}</span></h2></div></div>
                {activeOrders.length ? <div className="order-list">{activeOrders.map((order) => (
                    <OrderCard key={order.id} order={order}>
                        <span className="muted-note">Delivery: {formatStatus(order.delivery?.status || 'unassigned')}</span>
                        {nextDeliveryStatus(order) && <button className="button button-primary button-small" onClick={() => updateDelivery(order, nextDeliveryStatus(order).status)}>
                            {nextDeliveryStatus(order).label}
                        </button>}
                    </OrderCard>
                ))}</div> : <EmptyState title="No active deliveries" detail={orders.length ? 'You have completed your current assignments.' : 'A delivery will appear here when the system assigns you one.'} />}
            </section>
            {orders.some((order) => order.status === 'delivered') && <section className="section-block">
                <div className="section-heading"><div><span className="eyebrow">NICE WORK</span><h2>Completed orders</h2></div></div>
                <div className="order-list">{orders.filter((order) => order.status === 'delivered').map((order) => <OrderCard key={order.id} order={order} />)}</div>
            </section>}
        </div>
    );
};

export default DeliveryDashboard;
