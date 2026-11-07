import api from './api';

export const restaurantService = {
    list: async () => (await api.get('/restaurants/')).data,
    get: async (id) => (await api.get(`/restaurants/${id}`)).data,
    create: async (restaurant) => (await api.post('/restaurants/', restaurant)).data,
    addMenuItem: async (restaurantId, item) => (
        await api.post(`/restaurants/${restaurantId}/items`, item)
    ).data,
};
