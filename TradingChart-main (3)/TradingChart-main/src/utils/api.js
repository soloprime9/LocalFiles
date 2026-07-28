import axios from 'axios';
import { toast } from 'react-hot-toast';

// Create central Axios client
const api = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor: Logging in Development
api.interceptors.request.use(
  (config) => {
    if (import.meta.env.MODE === 'development') {
      console.log(`[API Request] -> ${config.method.toUpperCase()} ${config.url}`, config.params || config.data || '');
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response Interceptor: Centralized Toast and Error Handling
api.interceptors.response.use(
  (response) => {
    // Extract data wrapper based on backend response layout
    return response.data;
  },
  (error) => {
    const message = error.response?.data?.error || error.message || 'Something went wrong';
    
    // Prevent spamming toasts on cancellation or quick repeated lookups
    if (!axios.isCancel(error)) {
      toast.error(message, {
        id: 'api-error-toast', // Overwrite to prevent multiple duplicate popups
        style: {
          background: '#111111',
          color: '#FFFFFF',
          border: '1px solid #EF4444',
        },
      });
    }
    return Promise.reject(error);
  }
);

// ── INDICATORS ENDPOINTS ──────────────────────────────────────

export const getIndicators = (filters = {}) => {
  const params = { ...filters };
  
  // Convert arrays to comma-separated strings for backend controller compatibility
  if (Array.isArray(params.assetClass)) {
    params.assetClass = params.assetClass.join(',');
  }
  if (Array.isArray(params.strategyType)) {
    params.strategyType = params.strategyType.join(',');
  }
  
  return api.get('/indicators', { params });
};

export const getIndicator = (slug) => api.get(`/indicators/${slug}`);
export const getTrending = () => api.get('/indicators/trending');
export const getNewest = () => api.get('/indicators/new');
export const getFeatured = () => api.get('/indicators/featured');
export const getTopRated = () => api.get('/indicators/top-rated');
export const getFreeTools = () => api.get('/indicators/free');

export const getByListingType = (type) => api.get(`/indicators/type/${type}`);
export const getByAsset = (asset) => api.get(`/indicators/asset/${asset}`);
export const getByPlatform = (slug) => api.get(`/indicators/platform/${slug}`);
export const getByStrategy = (strategy) => api.get(`/indicators/strategy/${strategy}`);
export const getSimilar = (slug) => api.get(`/indicators/${slug}/similar`);

export const compareIndicators = (ids = []) => api.get('/indicators/compare', { params: { ids: ids.join(',') } });
export const incrementView = (id) => api.patch(`/indicators/${id}/view`);
export const toggleLike = (id) => api.patch(`/indicators/${id}/like`);
export const flagScam = (id, reason) => api.patch(`/indicators/${id}/flag-scam`, { reason });
export const createIndicator = (data) => api.post('/indicators', data);
export const getStats = () => api.get('/indicators/stats');

// ── REVIEWS ENDPOINTS ─────────────────────────────────────────

export const getReviews = (indicatorId) => api.get(`/reviews/indicator/${indicatorId}`);
export const createReview = (data) => api.post('/reviews', data);
export const markHelpful = (id) => api.patch(`/reviews/${id}/helpful`);
export const markNotHelpful = (id) => api.patch(`/reviews/${id}/not-helpful`);

// ── CATEGORIES ENDPOINTS ──────────────────────────────────────

export const getCategories = () => api.get('/categories');
export const getCategory = (slug) => api.get(`/categories/${slug}`);

// ── PLATFORMS ENDPOINTS ───────────────────────────────────────

export const getPlatforms = () => api.get('/platforms');
export const getPlatform = (slug) => api.get(`/platforms/${slug}`);

// ── SIGNALS ENDPOINTS ─────────────────────────────────────────

export const getSignals = (params) => api.get('/signals', { params });

// ── BROKERS ENDPOINTS ─────────────────────────────────────────

export const getBrokers = (params) => api.get('/brokers', { params });
export const getFeaturedBrokers = () => api.get('/brokers/featured');

// ── SUBMIT REQUESTS ───────────────────────────────────────────

export const submitListing = (data) => api.post('/submit', data);

// ── BLOG ENDPOINTS ────────────────────────────────────────────

export const getBlogPosts = (params) => api.get('/blog', { params });
export const getBlogPost = (slug) => api.get(`/blog/${slug}`);

export default api;






// import axios from 'axios';

// const api = axios.create({
//   baseURL: import.meta.env.VITE_API_URL || 'http://localhost:5000/api/v1',
//   headers: { 'Content-Type': 'application/json' },
// });

// export const createReview = (indicatorId, payload) =>
//   api.post(`/indicators/${indicatorId}/reviews`, payload).then((r) => r.data);

// export const markHelpful = (reviewId) =>
//   api.patch(`/reviews/${reviewId}/helpful`).then((r) => r.data);

// export const markNotHelpful = (reviewId) =>
//   api.patch(`/reviews/${reviewId}/not-helpful`).then((r) => r.data);

// export const flagScam = (indicatorId, reason) =>
//   api.post(`/indicators/${indicatorId}/flag`, { reason }).then((r) => r.data);

// export const fetchIndicators = (params) =>
//   api.get('/indicators', { params }).then((r) => r.data);

// export const fetchIndicatorBySlug = (slug) =>
//   api.get(`/indicators/${slug}`).then((r) => r.data);

// export default api;
