import asyncHandler from 'express-async-handler';
import { SocialInsight } from '../models/index.js';
import { GoogleGenAI, Type } from "@google/genai";

/**
 * @desc    Get all active ingested social insights/sentiment analytics
 * @route   GET /api/v1/social-insights
 * @access  Public
 */
export const getSocialInsights = asyncHandler(async (req, res) => {
  const { platform, sentiment, search, limit = 15 } = req.query;

  const query = {};

  if (platform && platform !== 'All') {
    query.platform = platform;
  }

  if (sentiment && sentiment !== 'All') {
    query.sentiment = sentiment;
  }

  if (search) {
    query.$or = [
      { title: { $regex: search, $options: 'i' } },
      { content: { $regex: search, $options: 'i' } },
      { author: { $regex: search, $options: 'i' } },
      { assetTags: { $regex: search, $options: 'i' } }
    ];
  }

  const limitNum = parseInt(limit, 10);

  const insights = await SocialInsight.find(query)
    .sort({ publishedAt: -1 })
    .limit(limitNum);

  res.status(200).json({
    success: true,
    count: insights.length,
    data: insights
  });
});

/**
 * @desc    Trigger autonomous AI Social Scraper (X, Reddit, Facebook, Instagram, YouTube)
 * @route   POST /api/v1/admin/automation/social-ingest
 * @access  Private (admin)
 */
export const runSocialScraping = asyncHandler(async (req, res) => {
  const { platform = 'Reddit', topic = 'TradingView Pine Script advanced strategy indicator', count = 3 } = req.body;

  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) {
    return res.status(500).json({
      success: false,
      error: 'GEMINI_API_KEY is not defined. Please configure secrets under Settings.'
    });
  }

  const ai = new GoogleGenAI({
    apiKey,
    httpOptions: {
      headers: {
        'User-Agent': 'aistudio-build'
      }
    }
  });

  try {
    const prompt = `
      You are an elite automated quantitative intelligence crawler and sentiment analyst.
      Your target platforms are: ['Twitter/X', 'Reddit', 'Facebook', 'Instagram', 'YouTube'].
      Use your live "googleSearch" tool parameter to scan for high-quality, actual public posts, threads, channels, and pages on "${platform}" discussing "${topic}".
      
      Look for actual shared setup rules, indicator configurations, Pine Script scripts, MT4 codes, risk parameters, or trading tricks that retail traders have publicly published.
      Do NOT manufacture fictional names, handles, or links. We want high-fidelity real information!
      
      Extract exactly ${count} distinct social assets from the "${platform}" indexing records today.
      
      For each asset:
      1. Choose the matching platform category: must be exactly one of: 'Twitter/X', 'Reddit', 'Facebook', 'Instagram', 'YouTube'
      2. Grab the author's official handle/name (e.g. "u/PineConnector" or "@QuantTraderX") and actual profile url if available
      3. Grab or extract a catching specific title of their setup/insight
      4. Get the complete post text (represented as "content" - max 400 characters)
      5. Construct an authoritative educational Strategy/Code workbook ("strategyShared" in rich markdown with code sections block) showing traders the systematic math or Pine Script rules shared
      6. Define sentiment bias ('Bullish', 'Neutral', 'Bearish'), relevance score (0-100), and target asset tags (e.g., ['BTC', 'ETH', 'EURUSD'])
      7. Keep sourceUrl holding the original social address/link.

      Ensure the returned information is formatted as a beautiful valid JSON array aligned with our schema.
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
              title: { type: Type.STRING, description: "Highly specific summary title of the shared social system/sentiment" },
              content: { type: Type.STRING, description: "Direct tweet/post body or concise highlight extract" },
              strategyShared: { type: Type.STRING, description: "Deeply structured Markdown strategy setup, input settings, or formulas. Avoid thin content." },
              platform: { 
                type: Type.STRING, 
                description: "Must be exactly one of: 'Twitter/X', 'Reddit', 'Facebook', 'Instagram', 'YouTube'" 
              },
              author: { type: Type.STRING, description: "Author handle without @ or u/, e.g., 'trading_wizard' or 'algorithmic_coder'" },
              authorAvatar: { type: Type.STRING, description: "Unsplash profile avatar photo URL or standard placeholder" },
              sentiment: { 
                type: Type.STRING, 
                description: "Must be exactly: 'Bullish', 'Neutral', 'Bearish'" 
              },
              relevanceScore: { type: Type.NUMBER, description: "A numerical rating from 0 to 100 on trading utility" },
              assetTags: { 
                type: Type.ARRAY, 
                items: { type: Type.STRING },
                description: "Symbols, e.g. ['BTC', 'SOL', 'USDT']" 
              },
              sourceUrl: { type: Type.STRING, description: "Target link to actual thread, post, profile, or video" }
            },
            required: [
              "title", "content", "strategyShared", "platform", "author", "sentiment", "relevanceScore", "assetTags", "sourceUrl"
            ]
          }
        },
        tools: [
          { googleSearch: {} }
        ]
      }
    });

    const items = JSON.parse(response.text.trim());
    const savedInsights = [];

    for (const item of items) {
      // Avoid duplicate title index within SocialInsight collection
      const exists = await SocialInsight.findOne({ title: { $regex: new RegExp('^' + item.title + '$', 'i') } });
      if (exists) {
        continue;
      }

      const defaultAvatars = [
        'https://images.unsplash.com/photo-1570295999919-56ceb5ecca61?auto=format&fit=crop&q=80&w=150',
        'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&q=80&w=150',
        'https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&q=80&w=150',
        'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&q=80&w=150'
      ];
      const randomAvatar = defaultAvatars[Math.floor(Math.random() * defaultAvatars.length)];

      const insightDoc = await SocialInsight.create({
        ...item,
        authorAvatar: item.authorAvatar || randomAvatar,
        publishedAt: new Date()
      });

      savedInsights.push(insightDoc);
    }

    res.status(200).json({
      success: true,
      message: `Social Alpha Scraper completed! Successfully parsed ${platform} indexes and archived ${savedInsights.length} premium trading insights to our database.`,
      data: savedInsights
    });

  } catch (error) {
    console.error('[AI Social Ingestion Core Failure]:', error);
    res.status(500).json({
      success: false,
      error: `Scraping error: ${error.message}`
    });
  }
});
