import { useCallback, useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { EmptyState, ErrorMessage, LoadingState } from '../../components/common/Feedback';
import OrderCard from '../../components/common/OrderCard';
import { useAuth } from '../../context/useAuth';
import { orderService } from '../../services/orderService';
import { formatMoney, getErrorMessage } from '../../utils/formatters';

const CustomerDashboard = () => {
    const { user } = useAuth();
    const location = useLocation();
    const [orders, setOrders] = useState([]);
    const [insights, setInsights] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [query, setQuery] = useState('');
    const [recommendation, setRecommendation] = useState(null);
    const [recommendationError, setRecommendationError] = useState('');
    const [asking, setAsking] = useState(false);
    const [actionError, setActionError] = useState('');

    const loadData = useCallback(async () => {
        setError('');
        const ordersRequest = orderService.listMine()
            .then(setOrders)
            .catch((requestError) => {
                setError(getErrorMessage(requestError, 'Could not load your order history.'));
            })
            .finally(() => setLoading(false));
        const insightsRequest = orderService.insights()
            .then(setInsights)
            .catch((requestError) => {
                setError((current) => current || getErrorMessage(requestError, 'Could not load your insights.'));
            });
        await Promise.all([ordersRequest, insightsRequest]);
    }, []);

    useEffect(() => {
        const timer = window.setTimeout(loadData, 0);
        return () => window.clearTimeout(timer);
    }, [loadData]);

    const cancelOrder = async (orderId) => {
        setActionError('');
        try {
            await orderService.updateStatus(orderId, 'cancelled');
            await loadData();
        } catch (requestError) {
            setActionError(getErrorMessage(requestError, 'Could not cancel this order.'));
        }
    };

    const askAdvisor = async (event) => {
        event.preventDefault();
        setAsking(true);
        setRecommendationError('');
        setRecommendation(null);
        try {
            setRecommendation(await orderService.askOrderHistory(query));
        } catch (requestError) {
            setRecommendationError(getErrorMessage(requestError, 'The food advisor is unavailable right now.'));
        } finally {
            setAsking(false);
        }
    };

    if (loading) return <LoadingState label="Loading your orders and insights..." />;

    return (
        <div className="content-stack">
            <section className="page-heading">
                <span className="eyebrow">YOUR CAMPUSBITE</span>
                <h1>Hey, {user?.full_name?.split(' ')[0] || 'there'}.</h1>
                <p>Keep an eye on your orders and discover what to try next.</p>
            </section>
            {location.state?.orderPlaced && <div className="notice notice-success">Order placed! The restaurant has received your order.</div>}
            <ErrorMessage message={error} />
            <ErrorMessage message={actionError} />
            {insights && (
                <section className="stats-grid">
                    <div className="stat-card"><span>ORDERS PLACED</span><strong>{insights.total_orders_analyzed}</strong><small>All-time</small></div>
                    <div className="stat-card"><span>SPENT ON DELIVERED ORDERS</span><strong>{formatMoney(insights.total_spent)}</strong><small>Your campus food total</small></div>
                    <div className="stat-card stat-card-accent"><span>YOUR GO-TO</span><strong className="stat-favorite">{insights.favorite_items?.[0] || 'To be discovered'}</strong><small>{insights.favorite_items?.length ? 'Favorite from your orders' : 'Place an order to build your profile'}</small></div>
                </section>
            )}
            <section className="section-block">
                <div className="section-heading"><div><span className="eyebrow">ORDER HISTORY</span><h2>Your orders</h2></div><Link className="text-link" to="/restaurants">Order something →</Link></div>
                {orders.length ? <div className="order-list">{orders.map((order) => (
                    <OrderCard key={order.id} order={order}>
                        {order.status === 'placed' && <button className="button button-danger button-small" onClick={() => cancelOrder(order.id)}>Cancel order</button>}
                        {order.review && <span className="review-summary">Your review: {order.review.rating}/5</span>}
                    </OrderCard>
                ))}</div> : <EmptyState title="No orders yet" detail="Your next campus favorite is waiting." action={<Link to="/restaurants" className="button button-primary">Browse restaurants</Link>} />}
            </section>
            <section className="advisor-panel">
                <div className="advisor-intro"><span className="advisor-sparkle">✦</span><span className="eyebrow">YOUR ORDER HISTORY, EXPLAINED</span><h2>Ask your CampusBite advisor.</h2><p>Get answers based on your own orders. Your history stays private to your account.</p></div>
                <div className="advisor-body">
                    <p className="advisor-recommendation">Try asking about recent orders, delivery status, this week’s spending, or your most ordered dishes.</p>
                    <div className="advisor-prompts">
                        {[
                            'Summarize my last five orders.',
                            'Which of my orders are still not delivered?',
                            'How much did I spend this week?',
                            'Which food items have I ordered most frequently?',
                        ].map((prompt) => (
                            <button className="advisor-prompt" type="button" key={prompt} onClick={() => setQuery(prompt)}>
                                {prompt}
                            </button>
                        ))}
                    </div>
                    <form className="advisor-form" onSubmit={askAdvisor}>
                        <label className="sr-only" htmlFor="food-query">What are you craving?</label>
                        <input id="food-query" required minLength={3} maxLength={1000} value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Ask a question about your orders..." />
                        <button className="button button-dark" disabled={asking}>{asking ? 'Checking your history...' : 'Ask advisor'}</button>
                    </form>
                    <ErrorMessage message={recommendationError} />
                    {recommendation && (
                        <div className="recommendation-result" role="status">
                            <p>{recommendation.answer}</p>
                            <small>Answered with {recommendation.provider} · Based on {recommendation.total_orders} of your orders ({recommendation.recent_orders_included} recent)</small>
                        </div>
                    )}
                </div>
            </section>
        </div>
    );
};

export default CustomerDashboard;
