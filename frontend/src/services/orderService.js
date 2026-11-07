import api from './api';

export const orderService = {
    create: async (order) => (await api.post('/orders/', order)).data,
    listMine: async () => (await api.get('/orders/me')).data,
    insights: async () => (await api.get('/orders/insights/summary')).data,
    restaurantAnalytics: async () => (await api.get('/orders/restaurant/analytics')).data,
    updateStatus: async (orderId, status) => (
        await api.patch(`/orders/${orderId}/status`, { status })
    ).data,
    askOrderHistory: async (question) => (
        await api.post('/orders/advisor', { question })
    ).data,
};
