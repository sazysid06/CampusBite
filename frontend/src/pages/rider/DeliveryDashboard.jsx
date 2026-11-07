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

    const loadOrders = useCallback(async () => {
        setError('');
        try {
            setOrders(await orderService.listMine());
        } catch (requestError) {
            setError(getErrorMessage(requestError, 'Could not load your assigned deliveries.'));
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        const timer = window.setTimeout(loadOrders, 0);
        return () => window.clearTimeout(timer);
    }, [loadOrders]);

    const advanceDelivery = async (order) => {
        const nextStatus = order.status === 'assigned' ? 'out_for_delivery' : 'delivered';
        setError('');
        try {
            await orderService.updateStatus(order.id, nextStatus);
            setNotice(`Order #${order.id} marked ${formatStatus(nextStatus).toLowerCase()}.`);
            setLoading(true);
            await loadOrders();
        } catch (requestError) {
            setError(getErrorMessage(requestError, 'Could not update delivery status.'));
        }
    };

    if (loading) return <LoadingState label="Checking your assigned deliveries..." />;

    const activeOrders = orders.filter((order) => ['assigned', 'out_for_delivery'].includes(order.status));

    return (
        <div className="content-stack">
            <section className="page-heading"><span className="eyebrow">DELIVERY PARTNER</span><h1>Every delivery matters.</h1><p>Your assigned campus orders, all in one place.</p></section>
            {notice && <div className="notice notice-success" role="status">{notice}</div>}
            <ErrorMessage message={error} />
            <section className="section-block">
                <div className="section-heading"><div><span className="eyebrow">YOUR ROUTE</span><h2>Active deliveries <span className="count-bubble">{activeOrders.length}</span></h2></div></div>
                {activeOrders.length ? <div className="order-list">{activeOrders.map((order) => (
                    <OrderCard key={order.id} order={order}>
                        <button className="button button-primary button-small" onClick={() => advanceDelivery(order)}>
                            {order.status === 'assigned' ? 'Confirm pickup' : 'Mark delivered'}
                        </button>
                    </OrderCard>
                ))}</div> : <EmptyState title="No active deliveries" detail={orders.length ? 'You have completed your current assignments.' : 'Assigned orders will appear here when a restaurant sends them your way.'} />}
            </section>
            {orders.some((order) => order.status === 'delivered') && <section className="section-block">
                <div className="section-heading"><div><span className="eyebrow">NICE WORK</span><h2>Completed orders</h2></div></div>
                <div className="order-list">{orders.filter((order) => order.status === 'delivered').map((order) => <OrderCard key={order.id} order={order} />)}</div>
            </section>}
        </div>
    );
};

export default DeliveryDashboard;
