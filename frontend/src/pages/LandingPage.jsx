import { Link } from 'react-router-dom';

const LandingPage = () => (
    <div className="app-frame landing-frame">
        <header className="topbar landing-topbar">
            <Link to="/" className="brand" aria-label="CampusBite home">
                <span className="brand-mark">C</span>
                <span>Campus<span className="brand-accent">Bite</span></span>
            </Link>
            <nav className="main-nav" aria-label="Main navigation">
                <a className="nav-link" href="#how-it-works">How it works</a>
            </nav>
            <div className="account-menu">
                <Link to="/login" className="button button-quiet">Sign in</Link>
                <Link to="/register" className="button button-primary">Create account</Link>
            </div>
        </header>

        <main className="page-content landing-content">
            <section className="landing-hero" aria-labelledby="landing-title">
                <div className="landing-copy">
                    <span className="eyebrow">YOUR CAMPUS, SERVED</span>
                    <h1 id="landing-title">Good food.<br />Right around campus.</h1>
                    <p>Discover local favorites, place an order, and keep up with every step—from the kitchen to your door.</p>
                    <div className="landing-actions">
                        <Link to="/register" className="button button-primary">Get started</Link>
                        <Link to="/login" className="button button-quiet">I already have an account</Link>
                    </div>
                    <span className="landing-note">Choose a customer, restaurant, or delivery account when you sign up.</span>
                </div>
                <div className="landing-art" aria-hidden="true">
                    <span className="landing-art-spark">✦</span>
                    <div className="landing-art-bowl">🍜</div>
                    <div className="landing-art-label">A little closer<br />to delicious</div>
                    <span className="landing-art-dot landing-art-dot-one" />
                    <span className="landing-art-dot landing-art-dot-two" />
                </div>
            </section>

            <section id="how-it-works" className="landing-features" aria-labelledby="features-title">
                <div className="landing-section-heading">
                    <span className="eyebrow">MADE FOR CAMPUS LIFE</span>
                    <h2 id="features-title">Good food brings everyone together.</h2>
                </div>
                <div className="landing-feature-grid">
                    <article className="landing-feature">
                        <span className="landing-feature-icon" aria-hidden="true">🍽️</span>
                        <h3>Find your next favorite</h3>
                        <p>Explore nearby campus restaurants, browse menus, and order what you’re craving.</p>
                    </article>
                    <article className="landing-feature">
                        <span className="landing-feature-icon" aria-hidden="true">🏪</span>
                        <h3>Run your restaurant</h3>
                        <p>Manage your menu and stay on top of incoming orders from one place.</p>
                    </article>
                    <article className="landing-feature">
                        <span className="landing-feature-icon" aria-hidden="true">🚲</span>
                        <h3>Deliver on campus</h3>
                        <p>Keep track of delivery work and help get meals where they need to go.</p>
                    </article>
                </div>
            </section>
        </main>

        <footer className="site-footer">
            <span>CampusBite</span>
            <span>Good food, around campus.</span>
        </footer>
    </div>
);

export default LandingPage;
