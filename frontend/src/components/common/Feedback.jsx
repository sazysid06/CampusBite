export const LoadingState = ({ label = 'Loading...' }) => (
    <div className="feedback-card" role="status"><span className="spinner" />{label}</div>
);

export const ErrorMessage = ({ message }) => message
    ? <div className="notice notice-error" role="alert">{message}</div>
    : null;

export const EmptyState = ({ title, detail, action }) => (
    <div className="empty-state">
        <div className="empty-mark">CB</div>
        <h2>{title}</h2>
        {detail && <p>{detail}</p>}
        {action}
    </div>
);
