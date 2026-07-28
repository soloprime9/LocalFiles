'use client'
import { createContext, useContext, useReducer, useEffect, useCallback } from 'react';

const AppContext = createContext(null);

const STORAGE_KEY = 'indicatorhub_compare';

const initialFilters = {
  search: '',
  listingType: 'All',
  platforms: [],
  assetClass: [],
  strategyType: [],
  timeframes: [],
  difficulty: [],
  freeOnly: false,
  minRating: 0,
  minWinRate: 0,
  sortBy: 'Trending',
};

function loadCompareList() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

const initialState = {
  filters: initialFilters,
  compareList: loadCompareList(),
};

function reducer(state, action) {
  switch (action.type) {
    case 'SET_FILTER':
      return { ...state, filters: { ...state.filters, [action.key]: action.value } };
    case 'TOGGLE_ARRAY_FILTER': {
      const current = state.filters[action.key] || [];
      const exists = current.includes(action.value);
      const next = exists
        ? current.filter((v) => v !== action.value)
        : [...current, action.value];
      return { ...state, filters: { ...state.filters, [action.key]: next } };
    }
    case 'RESET_FILTERS':
      return { ...state, filters: initialFilters };
    case 'ADD_TO_COMPARE': {
      if (state.compareList.some((i) => i._id === action.indicator._id)) return state;
      if (state.compareList.length >= 3) return state;
      return { ...state, compareList: [...state.compareList, action.indicator] };
    }
    case 'REMOVE_FROM_COMPARE':
      return { ...state, compareList: state.compareList.filter((i) => i._id !== action.id) };
    case 'CLEAR_COMPARE':
      return { ...state, compareList: [] };
    default:
      return state;
  }
}

export function AppProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, initialState);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state.compareList));
    } catch {
      // ignore storage errors
    }
  }, [state.compareList]);

  const setFilter = useCallback((key, value) => dispatch({ type: 'SET_FILTER', key, value }), []);
  const toggleArrayFilter = useCallback(
    (key, value) => dispatch({ type: 'TOGGLE_ARRAY_FILTER', key, value }),
    []
  );
  const resetFilters = useCallback(() => dispatch({ type: 'RESET_FILTERS' }), []);
  const addToCompare = useCallback(
    (indicator) => dispatch({ type: 'ADD_TO_COMPARE', indicator }),
    []
  );
  const removeFromCompare = useCallback((id) => dispatch({ type: 'REMOVE_FROM_COMPARE', id }), []);
  const clearCompare = useCallback(() => dispatch({ type: 'CLEAR_COMPARE' }), []);
  const isInCompare = useCallback(
    (id) => state.compareList.some((i) => i._id === id),
    [state.compareList]
  );

  const value = {
    filters: state.filters,
    compareList: state.compareList,
    setFilter,
    toggleArrayFilter,
    resetFilters,
    addToCompare,
    removeFromCompare,
    clearCompare,
    isInCompare,
    dispatch,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useAppContext() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useAppContext must be used within AppProvider');
  return ctx;
}
