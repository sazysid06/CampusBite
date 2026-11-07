import { formatMoney, formatStatus } from '../../utils/formatters';

const OrderCard = ({ order, restaurantName, children }) => (
    <article className="order-card">
        <div className="order-card-top">
            <div><span className="eyebrow">ORDER #{order.id}</span><h3>{restaurantName || `Restaurant #${order.restaurant_id}`}</h3></div>
            <span className={`status-pill status-${order.status}`}>{formatStatus(order.status)}</span>
        </div>
        <div className="order-items">
            {order.items?.map((item) => <span key={item.id}>{item.quantity} × menu item #{item.menu_item_id}</span>)}
        </div>
        <div className="order-card-bottom">
            <span>{new Date(order.created_at).toLocaleString()}</span>
            <strong>{formatMoney(order.total_amount)}</strong>
        </div>
        <div className="order-delivery-address">{order.delivery_address}</div>
        {children && <div className="order-actions">{children}</div>}
    </article>
);

export default OrderCard;
