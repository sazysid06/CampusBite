// User Roles matching backend enum definitions
export const ROLES = {
    CUSTOMER: 'customer',
    RESTAURANT_OWNER: 'restaurant_owner',
    DELIVERY_PARTNER: 'delivery_partner',
};

// 7-Stage CampusBite Order Lifecycle
export const ORDER_STATUS = {
    PLACED: 'PLACED',
    CONFIRMED: 'CONFIRMED',
    PREPARING: 'PREPARING',
    READY_FOR_PICKUP: 'READY_FOR_PICKUP',
    OUT_FOR_DELIVERY: 'OUT_FOR_DELIVERY',
    DELIVERED: 'DELIVERED',
    CANCELLED: 'CANCELLED',
};

// Visual status labels and UI badge colors
export const STATUS_CONFIG = {
    [ORDER_STATUS.PLACED]: { label: 'Order Placed', color: '#6b7280', bg: '#f3f4f6' },
    [ORDER_STATUS.CONFIRMED]: { label: 'Confirmed', color: '#2563eb', bg: '#dbeafe' },
    [ORDER_STATUS.PREPARING]: { label: 'Preparing', color: '#d97706', bg: '#fef3c7' },
    [ORDER_STATUS.READY_FOR_PICKUP]: { label: 'Ready for Pickup', color: '#7c3aed', bg: '#ede9fe' },
    [ORDER_STATUS.OUT_FOR_DELIVERY]: { label: 'Out for Delivery', color: '#0284c7', bg: '#e0f2fe' },
    [ORDER_STATUS.DELIVERED]: { label: 'Delivered', color: '#16a34a', bg: '#dcfce7' },
    [ORDER_STATUS.CANCELLED]: { label: 'Cancelled', color: '#dc2626', bg: '#fee2e2' },
};