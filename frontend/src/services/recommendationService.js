import api from './api';

export const recommendationService = {
    recommend: async (query) => (
        await api.post('/recommendations/', { query })
    ).data,
};
