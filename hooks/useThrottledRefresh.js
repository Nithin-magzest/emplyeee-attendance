import { useEffect } from 'react';

export function useThrottledRefresh(fetchCallback, refreshRateMs = 3500) {
  useEffect(() => {
    // Initial fetch
    fetchCallback();

    // Enforce controlled polling rate
    const interval = setInterval(() => {
      fetchCallback();
    }, refreshRateMs);

    return () => clearInterval(interval);
  }, [fetchCallback, refreshRateMs]);
}
