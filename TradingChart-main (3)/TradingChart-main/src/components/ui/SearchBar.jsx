'use client'
import { useState, useEffect, useRef } from 'react';
import { Search, X } from 'lucide-react';
import { useAppContext } from '../../context/AppContext';

export default function SearchBar({ className = '', autoFocus = false, placeholder = 'Search indicators, EAs, bots, strategies…' }) {
  const { filters, setFilter } = useAppContext();
  const [value, setValue] = useState(filters.search || '');
  const debounceRef = useRef(null);

  useEffect(() => {
    setValue(filters.search || '');
  }, [filters.search]);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      if (value !== filters.search) setFilter('search', value);
    }, 400);
    return () => clearTimeout(debounceRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  const handleClear = () => {
    setValue('');
    setFilter('search', '');
  };

  return (
    <div className={`relative ${className}`}>
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" />
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        autoFocus={autoFocus}
        placeholder={placeholder}
        className="w-full bg-[#0A0A0A] border border-[#1F2937] rounded-lg pl-9 pr-9 py-2 text-sm text-white placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-amber-500/50 focus:border-amber-500 transition-all"
      />
      {value && (
        <button
          type="button"
          onClick={handleClear}
          aria-label="Clear search"
          className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}
