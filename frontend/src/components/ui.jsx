export function Loading({ text = "Loading data..." }) {
  return (
    <div className="loading-container">
      <div className="loading-spinner" />
      <div className="loading-text">{text}</div>
    </div>
  );
}

export function ErrorDisplay({ message, onRetry }) {
  return (
    <div className="loading-container">
      <div style={{ fontSize: "1.5rem" }}>⚠️</div>
      <div className="loading-text">{message}</div>
      {onRetry && (
        <button onClick={onRetry} className="nav-btn active" style={{ marginTop: "8px" }}>
          Retry
        </button>
      )}
    </div>
  );
}