import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Provider } from 'react-redux';
import { store } from './store';
import { AppProvider } from './context/AppContext';
import { Layout } from './components/layout/Layout';
import { ProtectedRoute } from './components/ProtectedRoute';

// Operational and Strategy screens
import { Home } from './screens/Home';
import { Indicators } from './screens/Indicators';
import { IndicatorDetail } from './screens/IndicatorDetail';
import { Screener } from './screens/Screener';
import { News } from './screens/News';
import { MacroCalendar } from './screens/MacroCalendar';
import { Calculators } from './screens/Calculators';
import { Brokers } from './screens/Brokers';
import { Compare } from './screens/Compare';
import { SubmitListing } from './screens/SubmitListing';
import { Markets } from './screens/Markets';
import { Strategy } from './screens/Strategy';

// Authentication and user profile screens
import { Login } from './screens/Login';
import { Register } from './screens/Register';
import { Profile } from './screens/Profile';

// SEO Trust and Google legal compliance screens
import { AboutUs } from './screens/AboutUs';
import { PrivacyPolicy } from './screens/PrivacyPolicy';
import { TermsOfService } from './screens/TermsOfService';
import { Contact } from './screens/Contact';

const App = () => {
  return (
    <Provider store={store}>
      <AppProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Layout />}>
              <Route index element={<Home />} />
              <Route path="indicators" element={<Indicators />} />
              <Route path="indicators/:slug" element={<IndicatorDetail />} />
              <Route path="screener" element={<Screener />} />
              <Route path="news" element={<News />} />
              <Route path="macro-calendar" element={<MacroCalendar />} />
              <Route path="calculators" element={<Calculators />} />
              <Route path="brokers" element={<Brokers />} />
              <Route path="compare" element={<Compare />} />
              <Route path="submit" element={<SubmitListing />} />
              <Route path="markets" element={<Markets />} />
              <Route path="strategy" element={<Strategy />} />
              
              {/* Access corridors */}
              <Route path="login" element={<Login />} />
              <Route path="register" element={<Register />} />
              <Route path="profile" element={
                <ProtectedRoute>
                  <Profile />
                </ProtectedRoute>
              } />

              {/* SEO Core pages */}
              <Route path="about" element={<AboutUs />} />
              <Route path="privacy" element={<PrivacyPolicy />} />
              <Route path="terms" element={<TermsOfService />} />
              <Route path="contact" element={<Contact />} />

              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AppProvider>
    </Provider>
  );
};

export default App;
