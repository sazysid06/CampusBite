import api from './api';

export const authService = {
    // Login handler
    login: async (email, password) => {
        // If your backend uses OAuth2PasswordRequestForm, it requires URL-encoded form data with 'username':
        const formData = new URLSearchParams();
        formData.append('username', email);
        formData.append('password', password);

        const response = await api.post('/auth/login', formData, {
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
        });

        return response.data;
    },

    // Register handler
    register: async (userData) => {
        const response = await api.post('/auth/register', userData);
        return response.data;
    },

    // Get current user profile
    getCurrentUser: async () => {
        const response = await api.get('/auth/me');
        return response.data;
    },
};