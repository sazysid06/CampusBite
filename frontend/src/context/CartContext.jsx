import { useCallback, useEffect, useMemo, useState } from 'react';
import { CartContext } from './CartStateContext';

const readCart = () => {
    try {
        const saved = localStorage.getItem('cart');
        return saved ? JSON.parse(saved) : { restaurantId: null, restaurantName: '', items: [] };
    } catch {
        return { restaurantId: null, restaurantName: '', items: [] };
    }
};

export const CartProvider = ({ children }) => {
    const [cart, setCart] = useState(readCart);

    useEffect(() => {
        localStorage.setItem('cart', JSON.stringify(cart));
    }, [cart]);

    const addItem = useCallback((restaurant, item) => {
        if (cart.restaurantId && cart.restaurantId !== restaurant.id) return false;
        setCart((current) => {
            const existing = current.items.find((entry) => entry.id === item.id);
            return {
                restaurantId: restaurant.id,
                restaurantName: restaurant.name,
                items: existing
                    ? current.items.map((entry) => entry.id === item.id
                        ? { ...entry, quantity: entry.quantity + 1 }
                        : entry)
                    : [...current.items, { ...item, quantity: 1 }],
            };
        });
        return true;
    }, [cart.restaurantId]);

    const setQuantity = useCallback((itemId, quantity) => {
        setCart((current) => {
            const items = quantity > 0
                ? current.items.map((item) => item.id === itemId ? { ...item, quantity } : item)
                : current.items.filter((item) => item.id !== itemId);
            return items.length ? { ...current, items } : { restaurantId: null, restaurantName: '', items: [] };
        });
    }, []);

    const clearCart = useCallback(() => setCart({ restaurantId: null, restaurantName: '', items: [] }), []);
    const itemCount = cart.items.reduce((total, item) => total + item.quantity, 0);
    const total = cart.items.reduce((sum, item) => sum + item.price * item.quantity, 0);

    const value = useMemo(
        () => ({ cart, addItem, setQuantity, clearCart, itemCount, total }),
        [cart, addItem, clearCart, itemCount, setQuantity, total],
    );

    return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
};
