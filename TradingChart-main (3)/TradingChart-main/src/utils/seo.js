export function setSeo({ title, description, path = '' }) {
  document.title = title;
  const url = `https://falconspido.com${path}`;

  const upsert = (selector, attrName, attrValue, content) => {
    let el = document.head.querySelector(selector);
    if (!el) {
      el = document.createElement(attrName === 'rel' ? 'link' : 'meta');
      el.setAttribute(attrName, attrValue);
      document.head.appendChild(el);
    }
    attrName === 'rel' ? el.setAttribute('href', content) : el.setAttribute('content', content);
  };

  if (description) {
    upsert('meta[name="description"]', 'name', 'description', description);
    upsert('meta[property="og:description"]', 'property', 'og:description', description);
    upsert('meta[name="twitter:description"]', 'name', 'twitter:description', description);
  }
  upsert('meta[property="og:title"]', 'property', 'og:title', title);
  upsert('meta[name="twitter:title"]', 'name', 'twitter:title', title);
  upsert('meta[property="og:url"]', 'property', 'og:url', url);
  upsert('link[rel="canonical"]', 'rel', 'canonical', url);
}
