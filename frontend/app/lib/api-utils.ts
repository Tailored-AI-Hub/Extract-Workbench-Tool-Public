/**
 * API utility functions for error handling, retry logic, and request configuration
 */

export interface ApiError extends Error {
  status?: number;
  statusText?: string;
  data?: any;
}

export interface RetryConfig {
  maxRetries?: number;
  retryDelay?: number;
  retryableStatuses?: number[];
  shouldRetry?: (error: ApiError, attempt: number) => boolean;
}

export interface RequestConfig extends RequestInit {
  timeout?: number;
  retry?: RetryConfig;
}

const DEFAULT_RETRY_CONFIG: Required<RetryConfig> = {
  maxRetries: 3,
  retryDelay: 1000,
  retryableStatuses: [408, 429, 500, 502, 503, 504],
  shouldRetry: (error: ApiError, attempt: number) => {
    return (
      attempt < 3 &&
      (!error.status || [408, 429, 500, 502, 503, 504].includes(error.status))
    );
  },
};

/**
 * Creates an ApiError from a fetch response
 */
export async function createApiError(response: Response): Promise<ApiError> {
  let errorData: any;
  try {
    errorData = await response.json();
  } catch {
    errorData = { message: response.statusText };
  }

  const error = new Error(
    errorData.detail || errorData.message || `HTTP ${response.status}: ${response.statusText}`
  ) as ApiError;

  error.status = response.status;
  error.statusText = response.statusText;
  error.data = errorData;

  return error;
}

/**
 * Delays execution for a specified amount of time
 */
function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Calculates exponential backoff delay
 */
function getBackoffDelay(attempt: number, baseDelay: number): number {
  return baseDelay * Math.pow(2, attempt - 1);
}

/**
 * Fetches with timeout support
 */
async function fetchWithTimeout(
  url: string,
  options: RequestInit,
  timeoutMs: number = 30000
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    if ((error as Error).name === 'AbortError') {
      const timeoutError = new Error('Request timeout') as ApiError;
      timeoutError.status = 408;
      throw timeoutError;
    }
    throw error;
  }
}

/**
 * Enhanced fetch with retry logic and timeout
 */
export async function fetchWithRetry(
  url: string,
  config: RequestConfig = {}
): Promise<Response> {
  const { timeout = 30000, retry = {}, ...fetchOptions } = config;
  const retryConfig = { ...DEFAULT_RETRY_CONFIG, ...retry };

  let lastError: ApiError | null = null;
  let attempt = 0;

  while (attempt <= retryConfig.maxRetries) {
    try {
      const response = await fetchWithTimeout(url, fetchOptions, timeout);

      // If response is ok, return it
      if (response.ok) {
        return response;
      }

      // Create error from response
      lastError = await createApiError(response);

      // Check if we should retry
      const shouldRetry =
        attempt < retryConfig.maxRetries &&
        (retryConfig.shouldRetry
          ? retryConfig.shouldRetry(lastError, attempt)
          : retryConfig.retryableStatuses.includes(response.status));

      if (!shouldRetry) {
        throw lastError;
      }

      // Wait before retrying with exponential backoff
      const backoffDelay = getBackoffDelay(attempt + 1, retryConfig.retryDelay);
      await delay(backoffDelay);

      attempt++;
    } catch (error) {
      lastError = error as ApiError;

      // Check if we should retry on network errors
      const shouldRetry =
        attempt < retryConfig.maxRetries &&
        (retryConfig.shouldRetry
          ? retryConfig.shouldRetry(lastError, attempt)
          : lastError.status === 408 || lastError.message?.includes('fetch'));

      if (!shouldRetry) {
        throw lastError;
      }

      // Wait before retrying
      const backoffDelay = getBackoffDelay(attempt + 1, retryConfig.retryDelay);
      await delay(backoffDelay);

      attempt++;
    }
  }

  throw lastError || new Error('Request failed after retries');
}

/**
 * Request deduplication cache
 */
class RequestCache {
  private cache = new Map<string, Promise<Response>>();

  /**
   * Generates a cache key from URL and options
   */
  private getCacheKey(url: string, options: RequestInit): string {
    const method = options.method || 'GET';
    const body = options.body ? JSON.stringify(options.body) : '';
    return `${method}:${url}:${body}`;
  }

  /**
   * Gets or creates a cached request
   */
  async get(
    url: string,
    options: RequestInit,
    fetcher: () => Promise<Response>
  ): Promise<Response> {
    const key = this.getCacheKey(url, options);

    // Only cache GET requests
    if (options.method && options.method !== 'GET') {
      return fetcher();
    }

    if (this.cache.has(key)) {
      return this.cache.get(key)!.then((response) => response.clone());
    }

    const promise = fetcher().then((response) => {
      // Remove from cache after a short time to allow deduplication
      // but not cache the response indefinitely
      setTimeout(() => this.cache.delete(key), 1000);
      return response;
    });

    this.cache.set(key, promise);
    return promise.then((response) => response.clone());
  }

  /**
   * Clears the cache
   */
  clear(): void {
    this.cache.clear();
  }
}

export const requestCache = new RequestCache();

/**
 * Enhanced fetch with retry, timeout, and deduplication
 */
export async function enhancedFetch(
  url: string,
  config: RequestConfig = {}
): Promise<Response> {
  return requestCache.get(url, config, () => fetchWithRetry(url, config));
}
