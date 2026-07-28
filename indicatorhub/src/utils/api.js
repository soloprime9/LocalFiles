import axios from 'axios';
import toast from 'react-hot-toast';

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    if (process.env.NODE_ENV === 'development') {
      console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`, config.params || '');
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message =
      error.response?.data?.message ||
      error.response?.data?.error ||
      error.message ||
      'Something went wrong';
    if (error.response?.status !== 404) {
      toast.error(message);
    }
    return Promise.reject(error);
  }
);

// ── Indicators ──────────────────────────────────────────────
export const getIndicators = (params) => api.get('/indicators', { params });
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
export const compareIndicators = (ids) =>
  api.get('/indicators/compare', { params: { ids: ids.join(',') } });
export const incrementView = (id) => api.patch(`/indicators/${id}/view`);
export const toggleLike = (id) => api.patch(`/indicators/${id}/like`);
export const flagScam = (id, reason) => api.patch(`/indicators/${id}/flag-scam`, { reason });
export const createIndicator = (data) => api.post('/indicators', data);
export const getStats = () => api.get('/indicators/stats');

// ── Reviews ──────────────────────────────────────────────────
export const getReviews = (indicatorId) => api.get(`/reviews/indicator/${indicatorId}`);
export const createReview = (data) => api.post('/reviews', data);
export const markHelpful = (id) => api.patch(`/reviews/${id}/helpful`);

// ── Categories ───────────────────────────────────────────────
export const getCategories = () => api.get('/categories');
export const getCategory = (slug) => api.get(`/categories/${slug}`);

// ── Platforms ────────────────────────────────────────────────
export const getPlatforms = () => api.get('/platforms');
export const getPlatform = (slug) => api.get(`/platforms/${slug}`);

// ── Signals ──────────────────────────────────────────────────
export const getSignals = (params) => api.get('/signals', { params });

// ── Brokers ──────────────────────────────────────────────────
export const getBrokers = (params) => api.get('/brokers', { params });
export const getFeaturedBrokers = () => api.get('/brokers/featured');

// ── Submit ───────────────────────────────────────────────────
export const submitListing = (data) => api.post('/submit', data);

// ── Blog ─────────────────────────────────────────────────────
export const getBlogPosts = (params) => api.get('/blog', { params });
export const getBlogPost = (slug) => api.get(`/blog/${slug}`);

export default api;
