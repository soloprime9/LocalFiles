import axios from 'axios';

// Detect host environment
const API = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json'
  }
});

// Request interceptor to attach JWT auth token dynamically
API.interceptors.request.use(
  (config) => {
    const userInfo = localStorage.getItem('fs_user_info');
    if (userInfo) {
      try {
        const parsed = JSON.parse(userInfo);
        const token = parsed.token || parsed.data?.token;
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
      } catch (err) {
        console.error('Error parsing token from storage:', err);
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Generic interceptor
API.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API Error Response:', error.response?.data || error.message);
    return Promise.reject(error.response?.data || { success: false, error: error.message });
  }
);

export const apiService = {
  // Indicators & Listing Discovery
  async getIndicators(params) {
    return API.get('/indicators', { params });
  },

  async getIndicator(slug) {
    return API.get(`/indicators/${slug}`);
  },

  async getTrending() {
    return API.get('/indicators/trending');
  },

  async getStats() {
    return API.get('/indicators/stats');
  },

  async getSimilar(slug) {
    return API.get(`/indicators/${slug}/similar`);
  },

  async toggleLike(id) {
    return API.patch(`/indicators/${id}/like`);
  },

  async flagScam(id, reason) {
    return API.patch(`/indicators/${id}/flag-scam`, { reason });
  },

  async createIndicator(data) {
    return API.post('/indicators', data);
  },

  async getCompareList(ids) {
    return API.get('/indicators/compare', { params: { ids: ids.join(',') } });
  },

  // Categories
  async getCategories() {
    return API.get('/categories');
  },

  // Platforms
  async getPlatforms() {
    return API.get('/platforms');
  },

  // Reviews
  async getReviews(indicatorId) {
    return API.get(`/reviews/indicator/${indicatorId}`);
  },

  // Submit Review
  async submitReview(data) {
    return API.post('/reviews', data);
  },

  async upvoteReview(id) {
    return API.patch(`/reviews/${id}/helpful`);
  },

  // Live Market Pricing Proxy Feed
  async getLivePrices() {
    return API.get('/market-data/prices');
  },

  async getSymbolCandles(symbol, resolution = '1D', count = 30) {
    return API.get(`/market-data/candles/${symbol}`, { params: { resolution, count } });
  },

  // Interactive Technical Screener
  async getScreenerData(market) {
    return API.get('/screener', { params: { market } });
  },

  // Global Economic Volatility News
  async getMarketNews(params) {
    return API.get('/news', { params });
  },

  async getSingleArticle(slug) {
    return API.get(`/news/${slug}`);
  },

  // Volatility Alerts & Scheduled Events Calendar
  async getMacroCalendar(params) {
    return API.get('/macro-calendar', { params });
  },

  // Merchant Configurations Presets
  async getIndicatorPresets(indicatorId, params) {
    return API.get(`/presets/indicator/${indicatorId}`, { params });
  },

  async submitPreset(data) {
    return API.post('/presets', data);
  },

  async votePreset(id, direction) {
    return API.patch(`/presets/${id}/vote`, { direction });
  },

  // Crowd Backtest Audit Ledgers
  async getBacktestReports(indicatorId) {
    return API.get(`/backtest-reports/indicator/${indicatorId}`);
  },

  async submitBacktestReport(data) {
    return API.post('/backtest-reports', data);
  },

  // Mathematical Multi-Tier Calculators
  async calculatePositionSize(data) {
    return API.post('/calculator/position-size', data);
  },

  async calculateDcaGrid(data) {
    return API.post('/calculator/dca-presets', data);
  },

  // Signals
  async getSignals(params) {
    return API.get('/signals', { params });
  },

  // Broker Affiliations
  async getBrokers(params) {
    return API.get('/brokers', { params });
  },

  // AI Generation Extractor
  async extractAiDetails(url) {
    return API.post('/ai/extract', { url });
  },

  // Admin Submissions list & moderation
  async getPendingSubmissions() {
    return API.get('/admin/submissions');
  },

  async approveSubmission(id) {
    return API.put(`/admin/submissions/${id}/approve`);
  },

  async rejectSubmission(id) {
    return API.put(`/admin/submissions/${id}/reject`);
  },

  // User Authentication API endpoints
  async login(email, password) {
    return API.post('/auth/login', { email, password });
  },

  async register(name, email, password) {
    return API.post('/auth/register', { name, email, password });
  },

  async getProfile() {
    return API.get('/auth/profile');
  },

   async runAiDiscovery(keyword, count) {
    return API.post('/admin/automation/discover', { keyword, count });
  },

  async runAiNewsIngestion(topic, count) {
    return API.post('/admin/automation/generate-news', { topic, count });
  },

  async runAiBlogIngestion(topic, count) {
    return API.post('/admin/automation/generate-blog', { topic, count });
  },

  async runSocialScraping(platform, topic, count) {
    return API.post('/admin/automation/social-ingest', { platform, topic, count });
  },

  async getSocialInsights(platform, sentiment, search, limit = 15) {
    const params = {};
    if (platform) params.platform = platform;
    if (sentiment) params.sentiment = sentiment;
    if (search) params.search = search;
    if (limit) params.limit = limit;
    return API.get('/social-insights', { params });
  }
};
