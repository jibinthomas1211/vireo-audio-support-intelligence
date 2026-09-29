import { useState, useEffect, useCallback, useRef } from "react";

/**
 * Custom hook for API data fetching with loading/error states.
 */
export function useApi(fetchFn, enabled = true) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const requestId = useRef(0);

  const request = useCallback(() => {
    const currentRequest = ++requestId.current;
    fetchFn()
      .then((result) => {
        if (currentRequest !== requestId.current) return;
        setData(result);
        setError(null);
        setLoading(false);
      })
      .catch((err) => {
        if (currentRequest !== requestId.current) return;
        console.error("API Error:", err);
        setError(err.message);
        setLoading(false);
      });
  }, [fetchFn]);

  const refetch = useCallback(() => {
    setLoading(true);
    setError(null);
    request();
  }, [request]);

  useEffect(() => {
    if (!enabled) return;
    request();
  }, [request, enabled]);

  return { data, loading, error, refetch };
}
