import React, { createContext, useContext, useState, useEffect } from 'react';
import { apiService } from '../utils/api';

const AppContext = createContext(undefined);

export const AppProvider = ({ children }) => {
  const [categories, setCategories] = useState([]);
  const [platforms, setPlatforms] = useState([]);
  const [compareList, setCompareList] = useState([]);
  const [isLoading, setLoading] = useState(true);
  const [favorites, setFavorites] = useState(() => {
    const saved = localStorage.getItem('fs_favs');
    return saved ? JSON.parse(saved) : [];
  });

  useEffect(() => {
    const fetchMetadata = async () => {
      try {
        const [catRes, platRes] = await Promise.all([
          apiService.getCategories(),
          apiService.getPlatforms()
        ]);
        if (catRes?.success) setCategories(catRes.data);
        if (platRes?.success) setPlatforms(platRes.data);
      } catch (err) {
        console.error('Failed to pre-hydrate FalconSpido master catalogs:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchMetadata();
  }, []);

  const addToCompare = (indicator) => {
    if (compareList.some(item => item._id === indicator._id)) {
      return false;
    }
    if (compareList.length >= 3) {
      return false;
    }
    setCompareList(prev => [...prev, indicator]);
    return true;
  };

  const removeFromCompare = (id) => {
    setCompareList(prev => prev.filter(item => item._id !== id));
  };

  const clearCompare = () => {
    setCompareList([]);
  };

  const toggleFavorite = (id) => {
    setFavorites(prev => {
      const updated = prev.includes(id) ? prev.filter(item => item !== id) : [...prev, id];
      localStorage.setItem('fs_favs', JSON.stringify(updated));
      return updated;
    });
  };

  return (
    <AppContext.Provider value={{
      categories,
      platforms,
      compareList,
      addToCompare,
      removeFromCompare,
      clearCompare,
      isLoading,
      setLoading,
      favorites,
      toggleFavorite
    }}>
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used inside an AppProvider wrapper');
  }
  return context;
};
