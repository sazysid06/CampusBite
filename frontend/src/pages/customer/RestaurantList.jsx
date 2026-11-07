import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { EmptyState, ErrorMessage, LoadingState } from '../../components/common/Feedback';
import { restaurantService } from '../../services/restaurantService';
import { getErrorMessage } from '../../utils/formatters';

const RestaurantList = () => {
    const [restaurants, setRestaurants] = useState([]);
    const [search, setSearch] = useState('');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        restaurantService.list()
            .then(setRestaurants)
            .catch((requestError) => setError(getErrorMessage(requestError, 'Could not load restaurants.')))
            .finally(() => setLoading(false));
    }, []);

    const visibleRestaurants = useMemo(() => restaurants.filter((restaurant) => (
        restaurant.is_open
        && `${restaurant.name} ${restaurant.description || ''} ${restaurant.address}`
            .toLowerCase().includes(search.toLowerCase())
    )), [restaurants, search]);

    return (
        <div className="content-stack">
            <section className="welcome-banner">
                <div>
                    <span className="eyebrow">YOUR CAMPUS, SERVED</span>
                    <h1>Find your next<br /><span className="text-accent">favorite bite.</span></h1>
                    <p>Discover local kitchens and fresh favorites near you.</p>
                </div>
                <div className="banner-art" aria-hidden="true"><span>✦</span><strong>Good<br />food<br />mood.</strong></div>
            </section>

            <section className="section-block">
                <div className="section-heading">
                    <div><span className="eyebrow">MADE FOR YOUR BREAK</span><h2>Restaurants around you</h2></div>
                    <label className="search-field">
                        <span className="sr-only">Search restaurants</span>
                        <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search restaurants..." />
                    </label>
                </div>
                {error && <ErrorMessage message={error} />}
                {loading ? <LoadingState label="Finding open restaurants..." /> : visibleRestaurants.length
                    ? <div className="restaurant-grid">
                        {visibleRestaurants.map((restaurant, index) => (
                            <Link className="restaurant-card" to={`/restaurants/${restaurant.id}`} key={restaurant.id}>
                                <div className={`restaurant-cover cover-${index % 4}`}><span>{restaurant.name.slice(0, 1).toUpperCase()}</span><small>OPEN NOW</small></div>
                                <div className="restaurant-card-body">
                                    <div className="restaurant-title-row"><h3>{restaurant.name}</h3><span className="rating">★ 4.{8 - index % 3}</span></div>
                                    <p>{restaurant.description || 'Freshly prepared campus favorites.'}</p>
                                    <span className="restaurant-address">{restaurant.address}</span>
                                    <span className="text-link">Explore menu <span aria-hidden="true">→</span></span>
                                </div>
                            </Link>
                        ))}
                    </div>
                    : <EmptyState
                        title={search ? 'No matching restaurants' : restaurants.length ? 'No restaurants are open right now' : 'No restaurants listed yet'}
                        detail={search
                            ? 'Try another search.'
                            : restaurants.length
                                ? 'Check back soon for fresh campus favorites.'
                                : 'A restaurant owner can add a restaurant and menu from the owner dashboard.'}
                    />}
            </section>
        </div>
    );
};

export default RestaurantList;
