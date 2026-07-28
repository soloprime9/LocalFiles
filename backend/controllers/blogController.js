import asyncHandler from 'express-async-handler';
import { BlogPost } from '../models/index.js';
import { GoogleGenAI, Type } from "@google/genai";

/**
 * @desc    Get all published posts (paginated)
 * @route   GET /api/v1/blog
 * @access  Public
 */

  // const apiKeys = process.env.GEMINI_API_KEY;
  // console.log(apiKeys)

export const getAll = asyncHandler(async (req, res) => {
  const { page = 1, limit = 6, tag, category } = req.query;
  const skip = (parseInt(page) - 1) * parseInt(limit);

  const query = { status: 'published' };

  if (tag) {
    query.tags = tag;
  }

  if (category) {
    query.category = category;
  }

  const total = await BlogPost.countDocuments(query);
  const items = await BlogPost.find(query)
    .populate('relatedIndicators', 'name slug imageUrl rating')
    .sort({ publishedAt: -1 })
    .skip(skip)
    .limit(parseInt(limit));

  res.status(200).json({
    success: true,
    data: items,
    total,
    page: parseInt(page),
    pages: Math.ceil(total / parseInt(limit))
  });
});

/**
 * @desc    Get single blog post details and increment views stats
 * @route   GET /api/v1/blog/:slug
 * @access  Public
 */
export const getOne = asyncHandler(async (req, res) => {
  const post = await BlogPost.findOne({ slug: req.params.slug })
    .populate('relatedIndicators', 'name slug imageUrl rating price pricingModel isFree isVerified trustScore');

  if (!post) {
    return res.status(404).json({ success: false, error: 'Blog article not found' });
  }

  post.views += 1;
  await post.save();

  res.status(200).json({ success: true, data: post });
});

/**
 * @desc    Get featured blog guides
 * @route   GET /api/v1/blog/featured
 * @access  Public
 */
export const getFeatured = asyncHandler(async (req, res) => {
  const items = await BlogPost.find({ isFeatured: true, status: 'published' })
    .sort({ publishedAt: -1 })
    .limit(3);

  res.status(200).json({ success: true, data: items });
});

/**
 * @desc    Write / Publish a new blog post
 * @route   POST /api/v1/blog
 * @access  Public (admin)
 */
export const create = asyncHandler(async (req, res) => {
  const newPost = await BlogPost.create(req.body);
  res.status(201).json({ success: true, data: newPost });
});

/**
 * @desc    Trigger autonomous AI quant masterclass blog post generation
 * @route   POST /api/v1/admin/automation/generate-blog
 * @access  Private (admin)
 */
export const runAiBlogIngestion = asyncHandler(async (req, res) => {
  const { topic = 'TradingView Pine Script advanced quantitative strategies', count = 1 } = req.body;

  const apiKey = process.env.GEMINI_API_KEY;

  if (!apiKey) {
    return res.status(500).json({
      success: false,
      error: 'GEMINI_API_KEY is not defined. Please add key under Settings.'
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
      You are an expert quantitative research director and financial SEO editor.
      Search the web using your live "googleSearch" tool for top trending, popular, and deeply high-quality systematic trading ideas, indicator guides, or Pine Script techniques related to: "${topic}".
      
      We need to write exactly ${count} highly detailed educational blog post(s) to index on Google and provide extreme value to traders.
      
      For each post, compose:
      1. A professional, highly technical article title.
      2. A concise and compelling excerpt (tagline/summary) under 250 characters.
      3. A very rich, complete, long-form masterclass article in Markdown format (at least 6-10 paragraphs), including:
         - Core systematic philosophy / math indicators.
         - Actual code snippets or pseudo-algorithm guides with exact configuration settings.
         - Systematic trading playbook (Rules for entries, exits, stop losses, profit targets).
         - Real risk parameters and operational limitations.
         Ensure there is no spam, filler, or fluff. Keep it extremely readable and direct.
      
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
              title: { type: Type.STRING, description: "Captivating, technical masterclass title" },
              excerpt: { type: Type.STRING, description: "A high-quality 2-sentence summary/tagline" },
              content: { type: Type.STRING, description: "Long-form Markdown article mapping mathematical setups and exact trading systematic playbook" },
              tags: {
                type: Type.ARRAY,
                items: { type: Type.STRING },
                description: "Array of 3 useful lowercase tags, e.g. ['pinescript', 'strat', 'breakout']"
              },
              category: { type: Type.STRING, description: "Choose from: 'Masterclass', 'Pine Script Coding', 'Strategy Showcase', 'Indicator Analysis', 'Risk Management'" },
              coverImage: { type: Type.STRING, description: "Finance/tech Unsplash wallpaper URL" },
              readTime: { type: Type.NUMBER, description: "Estimated read time in minutes, e.g. 8" }
            },
            required: [
              "title", "excerpt", "content", "tags", "category", "coverImage", "readTime"
            ]
          }
        },
        tools: [
          { googleSearch: {} }
        ]
      }
    });

    const items = JSON.parse(response.text.trim());
    const savedPosts = [];

    for (const item of items) {
      // Duplicate check
      const exists = await BlogPost.findOne({ title: { $regex: new RegExp('^' + item.title + '$', 'i') } });
      if (exists) {
        continue;
      }

      const postDoc = await BlogPost.create({
        ...item,
        status: 'published',
        author: 'Falcon Automative Editor',
        publishedAt: new Date()
      });

      savedPosts.push(postDoc);
    }

    res.status(200).json({
      success: true,
      message: `AI Blog masterclass generation complete! Generated and published ${savedPosts.length} comprehensive technical guides for immediate SEO indexation.`,
      data: savedPosts
    });

  } catch (error) {
    console.error('[AI Blog Generation Failure]:', error);
    res.status(500).json({
      success: false,
      error: `Automation failure: ${error.message}`
    });
  }
});

