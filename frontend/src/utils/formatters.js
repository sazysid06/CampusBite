export const getErrorMessage = (error, fallback = 'Something went wrong. Please try again.') => {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
        return detail.map((entry) => `${entry.loc?.slice(1).join('.') || 'field'}: ${entry.msg}`).join(' · ');
    }
    return fallback;
};

export const formatMoney = (amount) => new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2,
}).format(Number(amount) || 0);

export const formatStatus = (status = '') => status
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
