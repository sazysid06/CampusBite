import { useEffect, useState } from 'react';
import { authService } from '../services/authService';
import { AuthContext } from './AuthStateContext';

export const AuthProvider = ({ children }) => {
    const [token, setToken] = useState(() => localStorage.getItem('token') || null);
    const [user, setUser] = useState(() => {
        const savedUser = localStorage.getItem('user');
        if (savedUser && savedUser !== 'undefined') {
            try {
                const profile = JSON.parse(savedUser);
                if (typeof profile.email === 'string' && profile.email.includes('@')) {
                    return profile;
                }
            } catch {
                return null;
            }
        }
        return null;
    });
    const [loading, setLoading] = useState(() => Boolean(localStorage.getItem('token')));

    useEffect(() => {
        const savedToken = localStorage.getItem('token');
        if (!savedToken) {
            return undefined;
        }

        let isMounted = true;
        authService.getCurrentUser()
            .then((profile) => {
                if (!isMounted) return;
                localStorage.setItem('user', JSON.stringify(profile));
                setUser(profile);
            })
            .catch(() => {
                if (!isMounted) return;
                localStorage.removeItem('token');
                localStorage.removeItem('user');
                setToken(null);
                setUser(null);
            })
            .finally(() => {
                if (isMounted) setLoading(false);
            });

        return () => {
            isMounted = false;
        };
    }, []);

    const login = async (email, password) => {
        setLoading(true);
        try {
            const data = await authService.login(email, password);
            const accessToken = data.access_token || data.token;

            if (!accessToken) {
                throw new Error('No access token returned by server.');
            }

            localStorage.setItem('token', accessToken);
            const userProfile = await authService.getCurrentUser();
            localStorage.setItem('user', JSON.stringify(userProfile));
            setToken(accessToken);
            setUser(userProfile);
            return userProfile;
        } catch (error) {
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            setToken(null);
            setUser(null);
            throw error;
        } finally {
            setLoading(false);
        }
    };

    const register = async (userData) => {
        setLoading(true);
        try {
            return await authService.register(userData);
        } finally {
            setLoading(false);
        }
    };

    const logout = () => {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        setToken(null);
        setUser(null);
    };

    return (
        <AuthContext.Provider
            value={{
                token,
                user,
                loading,
                isAuthenticated: !!token,
                login,
                register,
                logout,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
};