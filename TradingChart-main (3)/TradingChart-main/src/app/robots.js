export default function robots() {
  return {
    rules: [
      {
        userAgent: '*',
        allow: '/',
        disallow: ['/api/', '/admin/'],
      },
    ],
    sitemap: 'https://falconspido.com/sitemap.xml',
    host: 'https://falconspido.com',
  };
}
