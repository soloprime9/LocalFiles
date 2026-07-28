import Parser from 'rss-parser';
const rssParser = new Parser();
const NEWS_FEEDS = [
  'https://www.investing.com/rss/news_1.rss',
  'https://www.forexlive.com/feed/'
];
import asyncHandler from 'express-async-handler';
import MarketNews from '../models/MarketNews.js';
import { GoogleGenAI, Type } from "@google/genai";

/**
 * @desc    Get all market updates & flash news
 * @route   GET /api/v1/news
 * @access  Public
 */
export const getMarketNews = asyncHandler(async (req, res) => {
  const { assetClass, sentiment, limits, flashOnly } = req.query;
  const filter = {};

  if (assetClass) {
    filter.assetClassTags = assetClass;
  }
  if (sentiment) {
    filter.sentiment = sentiment;
  }
  if (flashOnly === 'true') {
    filter.isFlashAlert = true;
  }

  const limitNum = parseInt(limits || '15', 10);

  const news = await MarketNews.find(filter)
    .sort({ publishedAt: -1 })
    .limit(limitNum);

  res.status(200).json({
    success: true,
    count: news.length,
    data: news
  });
});

/**
 * @desc    Get single news article by slug
 * @route   GET /api/v1/news/:slug
 * @access  Public
 */
export const getSingleNews = asyncHandler(async (req, res) => {
  const { slug } = req.params;

  const article = await MarketNews.findOne({ slug });

  if (!article) {
    res.status(404);
    throw new Error('News story not found');
  }

  // Increment views
  article.views += 1;
  await article.save();

  res.status(200).json({
    success: true,
    data: article
  });
});

/**
 * @desc    Publish a news article (Admin simulation)
 * @route   POST /api/v1/news
 * @access  Public (Simulated protection with secret check)
 */
export const createNewsStory = asyncHandler(async (req, res) => {
  const secretKey = req.headers['x-admin-secret'];
  if (process.env.ADMIN_SECRET && secretKey !== process.env.ADMIN_SECRET) {
    res.status(401);
    throw new Error('Unauthorized access. Invalid or missing administrative keys.');
  }

  const news = await MarketNews.create(req.body);

  res.status(201).json({
    success: true,
    message: 'News story published successfully to IndicatorHub Global feeds',
    data: news
  });
});

/**
 * @desc    Trigger autonomous AI macroeconomic and market flash news ingestion
 * @route   POST /api/v1/admin/automation/generate-news
 * @access  Private (admin)
 */




export const runAiNewsIngestion = asyncHandler(async (req, res) => {
  const { count = 5 } = req.body;

  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) {
    return res.status(500).json({
      success: false,
      error: 'GEMINI_API_KEY is not defined. Please add key under Settings.'
    });
  }

  // 1. Pull REAL articles from RSS — no key, no AI guessing
  let rawItems = [];
  for (const feedUrl of NEWS_FEEDS) {
    try {
      const feed = await rssParser.parseURL(feedUrl);
      rawItems.push(...feed.items.map(i => ({
        title: i.title,
        snippet: i.contentSnippet || i.content || '',
        link: i.link
      })));
    } catch (err) {
      console.log(`[RSS] ${feedUrl} failed: ${err.message}`);
    }
  }

  // 2. Skip ones already stored, keep newest N
  const candidates = [];
  for (const item of rawItems) {
    const exists = await MarketNews.findOne({ sourceUrl: item.link });
    if (!exists) candidates.push(item);
    if (candidates.length >= count) break;
  }

  if (candidates.length === 0) {
    return res.status(200).json({ success: true, message: 'No new RSS articles found.', data: [] });
  }

  const ai = new GoogleGenAI({
    apiKey,
    httpOptions: { headers: { 'User-Agent': 'aistudio-build' } }
  });

  try {
    const prompt = `
      You are an expert financial journalist and macro analyst.
      Below are REAL, just-published market news items pulled from live RSS feeds.
      Do NOT invent facts beyond what is given — only rewrite, classify, and expand the
      analysis using the provided title/snippet.

      Source items:
      ${JSON.stringify(candidates, null, 2)}

      For EACH item, compose:
      1. A professional rewritten headline (title)
      2. A concise 2-3 sentence overview text (summary, max 300 characters)
      3. A deeply structured analytical body (content) in Markdown exploring direct impacts
         on retail traders, key support/resistance margins, and underlying risk factors —
         based on the given snippet, not invented data.
      4. Sentiment ('Bullish' | 'Neutral' | 'Bearish') and importance ('Low' | 'Medium' | 'High')
      5. Correctly target affected asset classes and symbols (e.g. BTC, EURUSD, XAUUSD, TSLA, AAPL)
      6. An author byline (e.g. "Falcon Intelligence Desk", "Senior Economist")
      7. Whether this represents an ultra-urgent momentum spike (isFlashAlert)

      Keep the ORIGINAL "link" value exactly as given for "sourceUrl" (do not alter it), and
      use the feed's site name as "source" (e.g. "Investing.com", "ForexLive").

      Output ONLY a valid JSON array matching the specified schema format.
    `;

    const response = await ai.models.generateContent({
      model: "gemini-3.5-flash",
      contents: prompt,
      config: {
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.ARRAY,
          items: {
            type: Type.OBJECT,
            properties: {
              title: { type: Type.STRING, description: "Professional, eye-catching financial headline" },
              summary: { type: Type.STRING, description: "A high-quality short excerpt, max 300 characters" },
              content: { type: Type.STRING, description: "Thorough analytical body with professional advice on trading risks in markdown format" },
              source: { type: Type.STRING, description: "Reliable source name, e.g. 'Investing.com', 'ForexLive'" },
              sourceUrl: { type: Type.STRING, description: "The original RSS article link, unchanged" },
              assetClassTags: { type: Type.ARRAY, items: { type: Type.STRING }, description: "Choose from: 'Crypto', 'Forex', 'Stocks', 'Indices', 'Commodities', 'Global Economy'" },
              symbolsAffected: { type: Type.ARRAY, items: { type: Type.STRING }, description: "Tickers, e.g. ['BTC', 'EURUSD', 'AAPL', 'NVDA']" },
              sentiment: { type: Type.STRING, description: "Must be exactly one of: 'Bullish', 'Neutral', 'Bearish'" },
              importance: { type: Type.STRING, description: "Must be exactly one of: 'Low', 'Medium', 'High'" },
              author: { type: Type.STRING, description: "Author name, e.g. 'Falcon Intelligence Desk', 'Senior Economist'" },
              coverImage: { type: Type.STRING, description: "High-quality finance Unsplash cover photo URL" },
              isFlashAlert: { type: Type.BOOLEAN, description: "Whether this represents an ultra-urgent momentum spike" }
            },
            required: ["title", "summary", "content", "source", "sourceUrl", "assetClassTags", "symbolsAffected", "sentiment", "importance", "author", "isFlashAlert"]
          }
        }
        // no googleSearch tool needed anymore — RSS already gave us real data
      }
    });

    const items = JSON.parse(response.text.trim());
    const savedArticles = [];
    const fallbackImage = 'https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?auto=format&fit=crop&q=80&w=800';

    for (const item of items) {
      const exists = await MarketNews.findOne({ sourceUrl: item.sourceUrl });
      if (exists) continue;

      const newsDoc = await MarketNews.create({
        ...item,
        coverImage: item.coverImage || fallbackImage,
        publishedAt: new Date()
      });
      savedArticles.push(newsDoc);
    }

    res.status(200).json({
      success: true,
      message: `Pulled ${candidates.length} real RSS articles. Successfully AI-processed and published ${savedArticles.length} new reports to the newsroom database.`,
      data: savedArticles
    });

  } catch (error) {
    console.error('[AI News Generation Failure]:', error);
    res.status(500).json({ success: false, error: `Ingestion halted: ${error.message}` });
  }
});





// export const runAiNewsIngestion = asyncHandler(async (req, res) => {
//   const { topic = 'crypto and global macro market news today', count = 3 } = req.body;

//   const apiKey = process.env.GEMINI_API_KEY;
//   if (!apiKey) {
//     return res.status(500).json({
//       success: false,
//       error: 'GEMINI_API_KEY is not defined. Please add key under Settings.'
//     });
//   }

//   const ai = new GoogleGenAI({
//     apiKey,
//     httpOptions: {
//       headers: {
//         'User-Agent': 'aistudio-build'
//       }
//     }
//   });

//   try {
//     const prompt = `
//       You are an expert financial journalist and macro analyst.
//       Search the web using your live "googleSearch" tool for the most high-impact, real, current macroeconomic trading headlines and market news today (pertaining to: "${topic}").
//       Focus on volatile events, central bank announcements (Fed CPI interest rates), key indicators, crypto breakouts (Bitcoin USDT Ether), or major company stock movements (AAPL, TSLA, NVDA).
      
//       Extract exactly ${count} distinct stories happening in our active market. Do NOT invent fake or placeholder listings.
      
//       For each story, compose:
//       1. A professional headline
//       2. A concise 2-3 sentence overview text
//       3. A deeply structured analytical body (content) in Markdown exploring direct impacts on retail traders, key support/resistance margins, and underlying risk factors.
//       4. Sentiment and importance classification.
//       5. Correctly target affected symbols (e.g. BTC, EURUSD, XAUUSD, TSLA, AAPL).
      
//       Output ONLY a valid JSON array matching the specified schema format.
//     `;

//     const response = await ai.models.generateContent({
//       model: "gemini-3.5-flash",
//       contents: prompt,
//       config: {
//         responseMimeType: "application/json",
//         responseSchema: {
//           type: Type.ARRAY,
//           items: {
//             type: Type.OBJECT,
//             properties: {
//               title: { type: Type.STRING, description: "Professional, eye-catching financial headline" },
//               summary: { type: Type.STRING, description: "A high-quality short excerpt, max 300 characters" },
//               content: { type: Type.STRING, description: "Thorough analytical body with professional advice on trading risks in markdown format" },
//               source: { type: Type.STRING, description: "Reliable source name, e.g. 'Bloomberg Terminal', 'CoinTelegraph', 'Reuters', 'Crypto Intelligence Feed'" },
//               sourceUrl: { type: Type.STRING, description: "Actual reference source link or webpage" },
//               assetClassTags: {
//                 type: Type.ARRAY,
//                 items: { type: Type.STRING },
//                 description: "Choose from: 'Crypto', 'Forex', 'Stocks', 'Indices', 'Commodities', 'Global Economy'"
//               },
//               symbolsAffected: {
//                 type: Type.ARRAY,
//                 items: { type: Type.STRING },
//                 description: "Tickers, e.g. ['BTC', 'EURUSD', 'AAPL', 'NVDA']"
//               },
//               sentiment: {
//                 type: Type.STRING,
//                 description: "Must be exactly one of: 'Bullish', 'Neutral', 'Bearish'"
//               },
//               importance: {
//                 type: Type.STRING,
//                 description: "Must be exactly one of: 'Low', 'Medium', 'High'"
//               },
//               author: { type: Type.STRING, description: "Author name, e.g. 'Falcon Intelligence Desk', 'Senior Economist'" },
//               coverImage: { type: Type.STRING, description: "High-quality finance Unsplash cover photo URL" },
//               isFlashAlert: { type: Type.BOOLEAN, description: "Whether this represents an ultra-urgent momentum spike" }
//             },
//             required: [
//               "title", "summary", "content", "source", "assetClassTags", "symbolsAffected", "sentiment", "importance", "author", "coverImage", "isFlashAlert"
//             ]
//           }
//         },
//         tools: [
//           { googleSearch: {} }
//         ]
//       }
//     });

//     const items = JSON.parse(response.text.trim());
//     const savedArticles = [];

//     for (const item of items) {
//       // Duplicate protection
//       const exists = await MarketNews.findOne({ title: { $regex: new RegExp('^' + item.title + '$', 'i') } });
//       if (exists) {
//         continue;
//       }

//       // Default Unsplash fallbacks
//       const fallbackImage = 'https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?auto=format&fit=crop&q=80&w=800';

//       const newsDoc = await MarketNews.create({
//         ...item,
//         coverImage: item.coverImage || fallbackImage,
//         publishedAt: new Date()
//       });

//       savedArticles.push(newsDoc);
//     }

//     res.status(200).json({
//       success: true,
//       message: `AI Market News Scraper finished! Successfully scoured channels and published ${savedArticles.length} premium authenticated global reports to our newsroom database.`,
//       data: savedArticles
//     });

//   } catch (error) {
//     console.error('[AI News Generation Failure]:', error);
//     res.status(500).json({
//       success: false,
//       error: `Ingestion halted: ${error.message}`
//     });
//   }
// });

