'use client'; 

import React, { useEffect, useState } from 'react';
import { BrowserRouter } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AppProvider } from '@/context/AppContext';
import './globals.css'; // Aapki global CSS path

export default function RootLayout({ children }) {
  const [mounted, setMounted] = useState(false);

  // SSR Hydration aur browser constraints ko sync karne ke liye
  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <html lang="en">
      <body className="bg-[#0B0B0B] antialiased">
        <AppProvider>
          {/* BrowserRouter ko pure application layout par maintain karein */}
          {mounted ? (
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
              {children}
            </BrowserRouter>
          ) : (
            // Pre-hydration clean layout placeholder skeleton for SEO crawlers
            <div className="min-h-screen bg-[#0B0B0B]" />
          )}
        </AppProvider>
      </body>
    </html>
  );
}
