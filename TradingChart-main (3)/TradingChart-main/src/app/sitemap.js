const SITE_URL = 'https://falconspido.com';

// Static, always-present routes. When the backend is live, fetch indicator
// slugs, category slugs, and blog slugs here too and concat them in —
// this file runs at build/request time on the server, so an awaited
// fetch() to your API is safe to add later.
export default function sitemap() {
  const staticRoutes = [
    { path: '/', priority: 1.0, changeFrequency: 'daily' },
    { path: '/indicators', priority: 0.9, changeFrequency: 'daily' },
    { path: '/trending', priority: 0.8, changeFrequency: 'daily' },
    { path: '/new', priority: 0.8, changeFrequency: 'daily' },
    { path: '/top-rated', priority: 0.8, changeFrequency: 'weekly' },
    { path: '/free', priority: 0.7, changeFrequency: 'weekly' },
    { path: '/categories', priority: 0.7, changeFrequency: 'weekly' },
    { path: '/platforms', priority: 0.7, changeFrequency: 'weekly' },
    { path: '/strategies', priority: 0.7, changeFrequency: 'weekly' },
    { path: '/ai-finder', priority: 0.6, changeFrequency: 'monthly' },
    { path: '/compare', priority: 0.5, changeFrequency: 'monthly' },
    { path: '/brokers', priority: 0.6, changeFrequency: 'weekly' },
    { path: '/signals', priority: 0.6, changeFrequency: 'weekly' },
    { path: '/submit', priority: 0.4, changeFrequency: 'monthly' },
    { path: '/blog', priority: 0.6, changeFrequency: 'weekly' },
    { path: '/about', priority: 0.3, changeFrequency: 'yearly' },
    { path: '/editorial-policy', priority: 0.4, changeFrequency: 'monthly' },
    { path: '/sitemap', priority: 0.2, changeFrequency: 'monthly' },
    { path: '/contact', priority: 0.3, changeFrequency: 'yearly' },
    { path: '/disclaimer', priority: 0.2, changeFrequency: 'yearly' },
    { path: '/privacy-policy', priority: 0.2, changeFrequency: 'yearly' },
    { path: '/terms', priority: 0.2, changeFrequency: 'yearly' },
  ];

  const now = new Date();

  return staticRoutes.map((route) => ({
    url: `${SITE_URL}${route.path}`,
    lastModified: now,
    changeFrequency: route.changeFrequency,
    priority: route.priority,
  }));
}
