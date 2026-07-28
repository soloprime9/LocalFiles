'use client';

import React, { useEffect, useState } from 'react';
import { BrowserRouter } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AppProvider } from '@/context/AppContext';

// This is the CLIENT half of the root layout. It owns routing, global
// context, and toasts. It does NOT own <html>/<head> metadata — that
// lives in app/layout.jsx (a server component) so title/meta tags are
// present in the initial server-rendered HTML for crawlers and link
// previews that don't execute JavaScript.
export default function ClientShell({ children }) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <AppProvider>
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
        // Pre-hydration placeholder. Real content for crawlers comes from
        // the static <head> metadata in layout.jsx, not from this div.
        <div className="min-h-screen bg-[#0B0B0B]" />
      )}
    </AppProvider>
  );
}
