import React, { createContext, useContext, useReducer, useEffect } from 'react';
import {
  getCategories,
  getPlatforms,
  getTrending,
  getFeatured,
  getStats,
} from '../utils/api';

// ── Initial State ─────────────────────────────────────────────
const initialState = {
  indicators: [],
  trending: [],
  featured: [],
  newest: [],
  topRated: [],
  categories: [],
  platforms: [],
  brokers: [],
  stats: null,
  compareList: [],
  filters: {
    search: '',
    platform: '',
    category: '',
    listingType: '',
    assetClass: [],
    strategyType: [],
    timeframe: '',
    difficulty: '',
    isFree: false,
    minRating: 0,
    minWinRate: 0,
    sort: 'trending',
    page: 1,
    limit: 12,
  },
  totalResults: 0,
  totalPages: 0,
  loading: { indicators: false, trending: false, featured: false },
  error: null,
};

// ── Actions ───────────────────────────────────────────────────
export const ACTIONS = {
  FETCH_START: 'FETCH_START',
  FETCH_INDICATORS_SUCCESS: 'FETCH_INDICATORS_SUCCESS',
  FETCH_TRENDING_SUCCESS: 'FETCH_TRENDING_SUCCESS',
  FETCH_FEATURED_SUCCESS: 'FETCH_FEATURED_SUCCESS',
  FETCH_NEWEST_SUCCESS: 'FETCH_NEWEST_SUCCESS',
  FETCH_TOP_RATED_SUCCESS: 'FETCH_TOP_RATED_SUCCESS',
  FETCH_CATEGORIES_SUCCESS: 'FETCH_CATEGORIES_SUCCESS',
  FETCH_PLATFORMS_SUCCESS: 'FETCH_PLATFORMS_SUCCESS',
  FETCH_BROKERS_SUCCESS: 'FETCH_BROKERS_SUCCESS',
  FETCH_STATS_SUCCESS: 'FETCH_STATS_SUCCESS',
  SET_FILTER: 'SET_FILTER',
  RESET_FILTERS: 'RESET_FILTERS',
  SET_PAGE: 'SET_PAGE',
  ADD_TO_COMPARE: 'ADD_TO_COMPARE',
  REMOVE_FROM_COMPARE: 'REMOVE_FROM_COMPARE',
  CLEAR_COMPARE: 'CLEAR_COMPARE',
  FETCH_ERROR: 'FETCH_ERROR',
};

// ── Reducer ───────────────────────────────────────────────────
function appReducer(state, action) {
  switch (action.type) {
    case ACTIONS.FETCH_START:
      return {
        ...state,
        loading: { ...state.loading, [action.payload]: true },
        error: null,
      };

    case ACTIONS.FETCH_INDICATORS_SUCCESS:
      return {
        ...state,
        indicators: action.payload.data || action.payload,
        totalResults: action.payload.total || 0,
        totalPages: action.payload.pages || 0,
        loading: { ...state.loading, indicators: false },
      };

    case ACTIONS.FETCH_TRENDING_SUCCESS:
      return {
        ...state,
        trending: action.payload,
        loading: { ...state.loading, trending: false },
      };

    case ACTIONS.FETCH_FEATURED_SUCCESS:
      return {
        ...state,
        featured: action.payload,
        loading: { ...state.loading, featured: false },
      };

    case ACTIONS.FETCH_NEWEST_SUCCESS:
      return { ...state, newest: action.payload };

    case ACTIONS.FETCH_TOP_RATED_SUCCESS:
      return { ...state, topRated: action.payload };

    case ACTIONS.FETCH_CATEGORIES_SUCCESS:
      return { ...state, categories: action.payload };

    case ACTIONS.FETCH_PLATFORMS_SUCCESS:
      return { ...state, platforms: action.payload };

    case ACTIONS.FETCH_BROKERS_SUCCESS:
      return { ...state, brokers: action.payload };

    case ACTIONS.FETCH_STATS_SUCCESS:
      return { ...state, stats: action.payload };

    case ACTIONS.SET_FILTER:
      return {
        ...state,
        filters: { ...state.filters, ...action.payload, page: 1 },
      };

    case ACTIONS.RESET_FILTERS:
      return { ...state, filters: { ...initialState.filters } };

    case ACTIONS.SET_PAGE:
      return {
        ...state,
        filters: { ...state.filters, page: action.payload },
      };

    case ACTIONS.ADD_TO_COMPARE:
      if (state.compareList.length >= 3) return state;
      if (state.compareList.find((i) => i._id === action.payload._id)) return state;
      return { ...state, compareList: [...state.compareList, action.payload] };

    case ACTIONS.REMOVE_FROM_COMPARE:
      return {
        ...state,
        compareList: state.compareList.filter((i) => i._id !== action.payload),
      };

    case ACTIONS.CLEAR_COMPARE:
      return { ...state, compareList: [] };

    case ACTIONS.FETCH_ERROR:
      return {
        ...state,
        error: action.payload,
        loading: { indicators: false, trending: false, featured: false },
      };

    default:
      return state;
  }
}

// ── Context ───────────────────────────────────────────────────
const AppContext = createContext(null);

export function AppProvider({ children }) {
  const [state, dispatch] = useReducer(appReducer, initialState);

  useEffect(() => {
    const fetchInitial = async () => {
      try {
        const [categoriesRes, platformsRes, trendingRes, featuredRes, statsRes] =
          await Promise.allSettled([
            getCategories(),
            getPlatforms(),
            getTrending(),
            getFeatured(),
            getStats(),
          ]);

        if (categoriesRes.status === 'fulfilled') {
          dispatch({ type: ACTIONS.FETCH_CATEGORIES_SUCCESS, payload: categoriesRes.value?.data || categoriesRes.value || [] });
        }
        if (platformsRes.status === 'fulfilled') {
          dispatch({ type: ACTIONS.FETCH_PLATFORMS_SUCCESS, payload: platformsRes.value?.data || platformsRes.value || [] });
        }
        if (trendingRes.status === 'fulfilled') {
          dispatch({ type: ACTIONS.FETCH_TRENDING_SUCCESS, payload: trendingRes.value?.data || trendingRes.value || [] });
        }
        if (featuredRes.status === 'fulfilled') {
          dispatch({ type: ACTIONS.FETCH_FEATURED_SUCCESS, payload: featuredRes.value?.data || featuredRes.value || [] });
        }
        if (statsRes.status === 'fulfilled') {
          dispatch({ type: ACTIONS.FETCH_STATS_SUCCESS, payload: statsRes.value?.data || statsRes.value || null });
        }
      } catch (err) {
        dispatch({ type: ACTIONS.FETCH_ERROR, payload: err.message });
      }
    };

    fetchInitial();
  }, []);

  return (
    <AppContext.Provider value={{ state, dispatch }}>
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) throw new Error('useApp must be used within AppProvider');
  return context;
}

export default AppContext;
