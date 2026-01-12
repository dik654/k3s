import { useState, useCallback } from 'react';
import axios, { AxiosRequestConfig, AxiosError } from 'axios';

interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

interface UseApiReturn<T> extends UseApiState<T> {
  execute: (config?: AxiosRequestConfig) => Promise<T | null>;
  reset: () => void;
}

export function useApi<T = any>(
  initialUrl?: string,
  initialConfig?: AxiosRequestConfig
): UseApiReturn<T> {
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    loading: false,
    error: null,
  });

  const execute = useCallback(
    async (config?: AxiosRequestConfig): Promise<T | null> => {
      const finalConfig = { ...initialConfig, ...config };
      const url = config?.url || initialUrl;

      if (!url) {
        setState((prev) => ({ ...prev, error: 'No URL provided' }));
        return null;
      }

      setState((prev) => ({ ...prev, loading: true, error: null }));

      try {
        const response = await axios({ url, ...finalConfig });
        setState({ data: response.data, loading: false, error: null });
        return response.data;
      } catch (err) {
        const error = err as AxiosError;
        const errorMessage =
          error.response?.data?.message ||
          error.message ||
          'An error occurred';
        setState({ data: null, loading: false, error: errorMessage });
        return null;
      }
    },
    [initialUrl, initialConfig]
  );

  const reset = useCallback(() => {
    setState({ data: null, loading: false, error: null });
  }, []);

  return { ...state, execute, reset };
}

export default useApi;
