import api from './api';

export const orderService = {
    create: async (order) => (await api.post('/orders/', order)).data,
    listMine: async () => (await api.get('/orders/me')).data,
    insights: async () => (await api.get('/orders/insights/summary')).data,
    restaurantAnalytics: async () => (await api.get('/orders/restaurant/analytics')).data,
    updateStatus: async (orderId, status) => (
        await api.patch(`/orders/${orderId}/status`, { status })
    ).data,
    updateDeliveryStatus: async (orderId, status) => (
        await api.patch(`/orders/${orderId}/delivery-status`, { status })
    ).data,
    getRiderAvailability: async () => (
        await api.get('/orders/rider/availability')
    ).data,
    setRiderAvailability: async (isAvailable) => (
        await api.patch('/orders/rider/availability', { is_available: isAvailable })
    ).data,
    requestRefund: async (orderId, reason) => (
        await api.post(`/orders/${orderId}/refund-request`, { reason })
    ).data,
    decideRefund: async (orderId, status, decisionNotes = null) => (
        await api.post(`/orders/${orderId}/refund-decision`, {
            status,
            decision_notes: decisionNotes,
        })
    ).data,
    askOrderHistory: async (question) => (
        await api.post('/orders/advisor', { question })
    ).data,
};
