import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AppProvider } from './context/AppContext';
import Layout from './components/layout/Layout';

// Pages
import Home from './pages/Home';
import Indicators from './pages/Indicators';
import IndicatorDetail from './pages/IndicatorDetail';
import { Trending, NewArrivals, TopRated, FreeTools } from './pages/ListPages';
import { Categories, CategoryPage } from './pages/Categories';
import { Platforms, PlatformPage } from './pages/Platforms';
import Compare from './pages/Compare';
import AIFinder from './pages/AIFinder';
import SubmitListing from './pages/SubmitListing';
import {
  Strategies,
  StrategyPage,
  AssetPage,
  ListingTypePage,
  Signals,
  Brokers,
  Blog,
  BlogPost,
  NotFound,
} from './pages/MiscPages';

export default function App() {
  return (
    <AppProvider>
      <BrowserRouter>
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              background: '#1A1A1A',
              color: '#fff',
              border: '1px solid #1F2937',
              fontSize: '13px',
            },
            success: { iconTheme: { primary: '#10B981', secondary: '#000' } },
            error: { iconTheme: { primary: '#EF4444', secondary: '#000' } },
          }}
        />

        <Routes>
          {/* AI Finder — full screen, no layout */}
          <Route path="/ai-finder" element={<AIFinder />} />

          {/* All other routes — wrapped in Layout */}
          <Route element={<Layout />}>
            <Route path="/" element={<Home />} />
            <Route path="/indicators" element={<Indicators />} />
            <Route path="/indicators/:slug" element={<IndicatorDetail />} />
            <Route path="/trending" element={<Trending />} />
            <Route path="/new" element={<NewArrivals />} />
            <Route path="/top-rated" element={<TopRated />} />
            <Route path="/free" element={<FreeTools />} />
            <Route path="/categories" element={<Categories />} />
            <Route path="/categories/:slug" element={<CategoryPage />} />
            <Route path="/platforms" element={<Platforms />} />
            <Route path="/platforms/:slug" element={<PlatformPage />} />
            <Route path="/strategies" element={<Strategies />} />
            <Route path="/strategies/:type" element={<StrategyPage />} />
            <Route path="/assets/:assetClass" element={<AssetPage />} />
            <Route path="/type/:listingType" element={<ListingTypePage />} />
            <Route path="/signals" element={<Signals />} />
            <Route path="/brokers" element={<Brokers />} />
            <Route path="/compare" element={<Compare />} />
            <Route path="/submit" element={<SubmitListing />} />
            <Route path="/blog" element={<Blog />} />
            <Route path="/blog/:slug" element={<BlogPost />} />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AppProvider>
  );
}
