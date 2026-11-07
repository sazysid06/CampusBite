import { useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '../../context/useAuth';
import { ROLES } from '../../utils/constants';

const Login = () => {
    const location = useLocation();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [success, setSuccess] = useState(
        location.state?.registered ? 'Account created successfully! Please sign in.' : ''
    );
    const [isSubmitting, setIsSubmitting] = useState(false);

    const { login } = useAuth();
    const navigate = useNavigate();

    const redirectByRole = (role) => {
        const origin = location.state?.from?.pathname;
        if (origin) return origin;

        switch (role) {
            case ROLES.RESTAURANT_OWNER:
                return '/owner/dashboard';
            case ROLES.DELIVERY_PARTNER:
                return '/rider/dashboard';
            case ROLES.CUSTOMER:
            default:
                return '/restaurants';
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setSuccess('');
        setIsSubmitting(true);

        try {
            const userProfile = await login(email, password);
            const destination = redirectByRole(userProfile?.role);
            navigate(destination, { replace: true });
        } catch (err) {
            const detail = err.response?.data?.detail;
            let message = 'Invalid email or password. Please try again.';

            if (typeof detail === 'string') {
                message = detail;
            } else if (Array.isArray(detail)) {
                message = detail
                    .map((d) => `${d.loc ? d.loc.slice(1).join('.') : 'field'}: ${d.msg}`)
                    .join(' | ');
            }

            setError(message);
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div style={styles.container}>
            <div style={styles.card}>
                <h2 style={styles.title}>Welcome Back</h2>
                <p style={styles.subtitle}>Sign in to your CampusBite account</p>

                {success && <div style={styles.successBanner}>{success}</div>}
                {error && <div style={styles.errorBanner}>{error}</div>}

                <form onSubmit={handleSubmit} style={styles.form}>
                    <div style={styles.fieldGroup}>
                        <label style={styles.label}>Email Address</label>
                        <input
                            type="email"
                            required
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder="e.g. student@campus.edu"
                            style={styles.input}
                            disabled={isSubmitting}
                        />
                    </div>

                    <div style={styles.fieldGroup}>
                        <label style={styles.label}>Password</label>
                        <input
                            type="password"
                            required
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="Enter your password"
                            style={styles.input}
                            disabled={isSubmitting}
                        />
                    </div>

                    <button
                        type="submit"
                        disabled={isSubmitting}
                        style={isSubmitting ? { ...styles.submitBtn, opacity: 0.7 } : styles.submitBtn}
                    >
                        {isSubmitting ? 'Signing in...' : 'Sign In'}
                    </button>
                </form>

                <p style={styles.footerText}>
                    Don't have an account?{' '}
                    <Link to="/register" style={styles.link}>
                        Register here
                    </Link>
                </p>
            </div>
        </div>
    );
};

const styles = {
    container: {
        minHeight: '80vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1rem',
    },
    card: {
        width: '100%',
        maxWidth: '420px',
        backgroundColor: '#ffffff',
        borderRadius: '8px',
        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
        padding: '2rem',
        border: '1px solid #e5e7eb',
    },
    title: {
        margin: 0,
        fontSize: '1.5rem',
        fontWeight: '700',
        color: '#111827',
        textAlign: 'center',
    },
    subtitle: {
        margin: '0.5rem 0 1.5rem 0',
        fontSize: '0.875rem',
        color: '#6b7280',
        textAlign: 'center',
    },
    successBanner: {
        backgroundColor: '#dcfce7',
        color: '#15803d',
        padding: '0.75rem',
        borderRadius: '6px',
        fontSize: '0.875rem',
        marginBottom: '1rem',
        border: '1px solid #bbf7d0',
    },
    errorBanner: {
        backgroundColor: '#fee2e2',
        color: '#b91c1c',
        padding: '0.75rem',
        borderRadius: '6px',
        fontSize: '0.875rem',
        marginBottom: '1rem',
        border: '1px solid #fecaca',
    },
    form: {
        display: 'flex',
        flexDirection: 'column',
        gap: '1.25rem',
    },
    fieldGroup: {
        display: 'flex',
        flexDirection: 'column',
        gap: '0.4rem',
    },
    label: {
        fontSize: '0.875rem',
        fontWeight: '500',
        color: '#374151',
    },
    input: {
        padding: '0.65rem 0.85rem',
        borderRadius: '6px',
        border: '1px solid #d1d5db',
        fontSize: '0.95rem',
        outline: 'none',
    },
    submitBtn: {
        marginTop: '0.5rem',
        padding: '0.75rem',
        borderRadius: '6px',
        border: 'none',
        backgroundColor: '#2563eb',
        color: '#ffffff',
        fontSize: '1rem',
        fontWeight: '600',
        cursor: 'pointer',
        transition: 'background-color 0.2s ease',
    },
    footerText: {
        marginTop: '1.5rem',
        textAlign: 'center',
        fontSize: '0.875rem',
        color: '#6b7280',
    },
    link: {
        color: '#2563eb',
        textDecoration: 'none',
        fontWeight: '500',
    },
};

export default Login;