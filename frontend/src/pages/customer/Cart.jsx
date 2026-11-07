import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { EmptyState, ErrorMessage } from '../../components/common/Feedback';
import { useCart } from '../../context/useCart';
import { orderService } from '../../services/orderService';
import { formatMoney, getErrorMessage } from '../../utils/formatters';

const Cart = () => {
    const navigate = useNavigate();
    const { cart, setQuantity, clearCart, total } = useCart();
    const [deliveryAddress, setDeliveryAddress] = useState('');
    const [instructions, setInstructions] = useState('');
    const [error, setError] = useState('');
    const [submitting, setSubmitting] = useState(false);

    const checkout = async (event) => {
        event.preventDefault();
        setError('');
        setSubmitting(true);
        try {
            await orderService.create({
                restaurant_id: cart.restaurantId,
                delivery_address: deliveryAddress,
                special_instructions: instructions || null,
                items: cart.items.map((item) => ({ menu_item_id: item.id, quantity: item.quantity })),
            });
            clearCart();
            navigate('/dashboard', { state: { orderPlaced: true } });
        } catch (requestError) {
            setError(getErrorMessage(requestError, 'Your order could not be placed.'));
        } finally {
            setSubmitting(false);
        }
    };

    if (!cart.items.length) {
        return <EmptyState title="Your cart is hungry" detail="Add something delicious from a restaurant menu." action={<Link className="button button-primary" to="/restaurants">Explore restaurants</Link>} />;
    }

    return (
        <div className="content-stack narrow-content">
            <div className="page-heading"><span className="eyebrow">ONE LAST THING</span><h1>Your cart</h1><p>Ordering from <strong>{cart.restaurantName}</strong></p></div>
            <section className="panel">
                <div className="cart-lines">
                    {cart.items.map((item) => (
                        <div className="cart-line" key={item.id}>
                            <div><h3>{item.name}</h3><span>{formatMoney(item.price)} each</span></div>
                            <div className="quantity-control">
                                <button aria-label={`Decrease ${item.name}`} onClick={() => setQuantity(item.id, item.quantity - 1)}>−</button>
                                <span>{item.quantity}</span>
                                <button aria-label={`Increase ${item.name}`} onClick={() => setQuantity(item.id, item.quantity + 1)}>+</button>
                            </div>
                            <strong>{formatMoney(item.price * item.quantity)}</strong>
                        </div>
                    ))}
                </div>
                <div className="cart-total"><span>Total</span><strong>{formatMoney(total)}</strong></div>
            </section>
            <section className="panel">
                <h2>Delivery details</h2>
                <ErrorMessage message={error} />
                <form className="form-grid" onSubmit={checkout}>
                    <label className="field field-wide">Delivery address<input required minLength={5} maxLength={255} value={deliveryAddress} onChange={(event) => setDeliveryAddress(event.target.value)} placeholder="Dorm, building, room or pickup point" /></label>
                    <label className="field field-wide">Special instructions <span className="optional">(optional)</span><textarea rows="3" maxLength={500} value={instructions} onChange={(event) => setInstructions(event.target.value)} placeholder="Anything the restaurant or rider should know?" /></label>
                    <p className="mock-payment-note">Secure checkout · Demo payment is processed by the backend.</p>
                    <button className="button button-primary button-block field-wide" disabled={submitting}>{submitting ? 'Placing your order...' : `Place order · ${formatMoney(total)}`}</button>
                </form>
            </section>
        </div>
    );
};

export default Cart;
