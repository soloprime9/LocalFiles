import 'dotenv/config'; // <--- ISE SABSE UPAR LINE 1 PAR RAKHEIN

import express from 'express';
import path from 'path';
import cors from 'cors';
import helmet from 'helmet';
import rateLimit from 'express-rate-limit';
// import dotenv from 'dotenv';

// Load config environment variables
// dotenv.config();

// Imports from local folders
import connectDB from './config/db.js';
import router from './routes/index.js';
import { Indicator } from './models/index.js';
import errorHandler from './middleware/errorHandler.js';

async function startServer() {
  const app = express();
  const PORT = process.env.PORT || 5000;

  // Trust reverse proxy headers
  app.set('trust proxy', 1);

  // 1. Establish Database Connection
  await connectDB();

  // 2. Security Middleware Headers
  app.use(helmet({
    contentSecurityPolicy: false,
    crossOriginEmbedderPolicy: false
  }));
 
  // CORS configured for local clients
  app.use(cors({
    origin: [
      process.env.CLIENT_URL || 'http://localhost:5173',
      'http://localhost:3000',"falconspido.com","https://falconspido.com"
    ],
    credentials: true
  }));

  // 3. Body Parsing
  app.use(express.json());
  app.use(express.urlencoded({ extended: true }));

  // 4. Rate Limiting Configurations (Mitigate spamming)
  const apiLimiter = rateLimit({
    windowMs: 15 * 60 * 1000,
    max: 120,
    standardHeaders: true,
    legacyHeaders: false,
    message: { success: false, error: 'Too many API requests. Please try again later.' }
  });

  const submissionLimiter = rateLimit({
    windowMs: 15 * 60 * 1000,
    max: 10,
    standardHeaders: true,
    legacyHeaders: false,
    message: { success: false, error: 'Form limits reached. Please try again after 15 minutes.' }
  });

  app.use('/api/', apiLimiter);
  app.use('/api/v1/submit', submissionLimiter);
  app.use('/api/v1/reviews', submissionLimiter);

  // 5. Mount API Routes
  app.use('/api/v1', router);

  // 6. Serve Dynamic SEO Sitemap.xml
  app.get('/sitemap.xml', async (req, res) => {
    try {
      const activeItems = await Indicator.find({ status: 'active' }).select('slug updatedAt');
      const websiteUrl = process.env.CLIENT_URL || 'https://falconspido.com';
      
      let xml = '<?xml version="1.0" encoding="UTF-8"?>\n';
      xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n';
      
      xml += `  <url>\n    <loc>${websiteUrl}/</loc>\n    <changefreq>daily</changefreq>\n    <priority>1.0</priority>\n  </url>\n`;
      xml += `  <url>\n    <loc>${websiteUrl}/indicators</loc>\n    <changefreq>daily</changefreq>\n    <priority>0.9</priority>\n  </url>\n`;
      
      for (const item of activeItems) {
        const lastMod = item.updatedAt ? new Date(item.updatedAt).toISOString().split('T')[0] : new Date().toISOString().split('T')[0];
        xml += `  <url>\n    <loc>${websiteUrl}/indicators/${item.slug}</loc>\n    <lastmod>${lastMod}</lastmod>\n    <changefreq>weekly</changefreq>\n    <priority>0.8</priority>\n  </url>\n`;
      }
      
      xml += '</urlset>';
      res.header('Content-Type', 'application/xml');
      res.status(200).send(xml);
    } catch (err) {
      console.error('[Standalone Sitemap Failure]:', err);
      res.status(500).send('Error compiling standalone sitemap');
    }
  });

  // 7. Base Health Check Route
  app.get('/', (req, res) => {
    res.json({ message: 'FalconSpido Quant Directory API is fully active and synchronized!' });
  });

  // 8. Error handling
  app.use(errorHandler);

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`[Standalone Backend API Backend] online on port ${PORT}`);
  });
}

startServer();
