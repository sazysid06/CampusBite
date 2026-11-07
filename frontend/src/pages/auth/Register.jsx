import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../context/useAuth';
import { ROLES } from '../../utils/constants';

const Register = () => {
    const [formData, setFormData] = useState({
        fullName: '',
        email: '',
        phoneNumber: '',
        password: '',
        role: ROLES.CUSTOMER,
    });
    const [error, setError] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);

    const { register } = useAuth();
    const navigate = useNavigate();

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData((prev) => ({ ...prev, [name]: value }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setIsSubmitting(true);

        try {
            await register({
                full_name: formData.fullName,
                email: formData.email,
                phone_number: formData.phoneNumber,
                password: formData.password,
                role: formData.role,
            });
            navigate('/login', { state: { registered: true } });
        } catch (err) {
            const detail = err.response?.data?.detail;
            let message = 'Registration failed. Please check your details.';

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
                <h2 style={styles.title}>Create an Account</h2>
                <p style={styles.subtitle}>Join CampusBite to order, sell, or deliver</p>

                {error && <div style={styles.errorBanner}>{error}</div>}

                <form onSubmit={handleSubmit} style={styles.form}>
                    <div style={styles.fieldGroup}>
                        <label style={styles.label}>Full Name</label>
                        <input
                            type="text"
                            name="fullName"
                            required
                            value={formData.fullName}
                            onChange={handleChange}
                            placeholder="e.g. Alex Morgan"
                            style={styles.input}
                            disabled={isSubmitting}
                        />
                    </div>

                    <div style={styles.fieldGroup}>
                        <label style={styles.label}>Email Address</label>
                        <input
                            type="email"
                            name="email"
                            required
                            value={formData.email}
                            onChange={handleChange}
                            placeholder="e.g. alex@campus.edu"
                            style={styles.input}
                            disabled={isSubmitting}
                        />
                    </div>

                    <div style={styles.fieldGroup}>
                        <label style={styles.label}>Phone Number</label>
                        <input
                            type="tel"
                            name="phoneNumber"
                            required
                            value={formData.phoneNumber}
                            onChange={handleChange}
                            placeholder="e.g. 9876543210"
                            style={styles.input}
                            disabled={isSubmitting}
                        />
                    </div>

                    <div style={styles.fieldGroup}>
                        <label style={styles.label}>Password</label>
                        <input
                            type="password"
                            name="password"
                            required
                            minLength={8}
                            value={formData.password}
                            onChange={handleChange}
                            placeholder="Minimum 8 characters"
                            style={styles.input}
                            disabled={isSubmitting}
                        />
                    </div>

                    <div style={styles.fieldGroup}>
                        <label style={styles.label}>Account Role</label>
                        <select
                            name="role"
                            value={formData.role}
                            onChange={handleChange}
                            style={styles.select}
                            disabled={isSubmitting}
                        >
                            <option value={ROLES.CUSTOMER}>Customer (Order food & AI insights)</option>
                            <option value={ROLES.RESTAURANT_OWNER}>Restaurant Owner (Manage menus & orders)</option>
                            <option value={ROLES.DELIVERY_PARTNER}>Delivery Partner (Deliver orders)</option>
                        </select>
                    </div>

                    <button
                        type="submit"
                        disabled={isSubmitting}
                        style={isSubmitting ? { ...styles.submitBtn, opacity: 0.7 } : styles.submitBtn}
                    >
                        {isSubmitting ? 'Creating account...' : 'Create Account'}
                    </button>
                </form>

                <p style={styles.footerText}>
                    Already have an account?{' '}
                    <Link to="/login" style={styles.link}>
                        Sign in
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
        maxWidth: '440px',
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
        gap: '1.15rem',
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
    select: {
        padding: '0.65rem 0.85rem',
        borderRadius: '6px',
        border: '1px solid #d1d5db',
        fontSize: '0.95rem',
        outline: 'none',
        backgroundColor: '#ffffff',
        cursor: 'pointer',
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

export default Register;