import mongoose from 'mongoose';
import slugify from 'slugify';

const marketNewsSchema = new mongoose.Schema({
  title: {
    type: String,
    required: [true, 'News title is required'],
    trim: true,
    unique: true,
    maxlength: [200, 'Title cannot exceed 200 characters']
  },
  slug: {
    type: String,
    unique: true,
    lowercase: true
  },
  summary: {
    type: String,
    required: [true, 'News summary is required'],
    maxlength: [500, 'Summary cannot exceed 500 characters']
  },
  content: {
    type: String,
    required: [true, 'Markdown body is required']
  },
  source: {
    type: String,
    default: 'IndicatorHub Newsroom'
  },
  sourceUrl: {
    type: String
  },
  assetClassTags: [{
    type: String,
    enum: ['Crypto', 'Forex', 'Stocks', 'Indices', 'Commodities', 'Global Economy']
  }],
  symbolsAffected: [String], // e.g. ["BTC", "EURUSD", "AAPL", "XAUUSD"]
  sentiment: {
    type: String,
    enum: ['Bullish', 'Neutral', 'Bearish'],
    default: 'Neutral'
  },
  importance: {
    type: String,
    enum: ['Low', 'Medium', 'High'],
    default: 'Medium'
  },
  author: {
    type: String,
    default: 'Senior Market Strategist'
  },
  coverImage: {
    type: String,
    default: 'https://placehold.co/800x450/0f0f15/f59e0b?text=Market+News'
  },
  views: {
    type: Number,
    default: 0
  },
  isFlashAlert: {
    type: Boolean,
    default: false
  },
  publishedAt: {
    type: Date,
    default: Date.now
  }
}, {
  timestamps: true
});

// marketNewsSchema.index({ slug: 1 });
marketNewsSchema.index({ publishedAt: -1 });
marketNewsSchema.index({ assetClassTags: 1 });

marketNewsSchema.pre('save', function(next) {
  if (this.isModified('title')) {
    this.slug = slugify(this.title, { lower: true, strict: true });
  }
  next();
});

const MarketNews = mongoose.models.MarketNews || mongoose.model('MarketNews', marketNewsSchema);
export default MarketNews;
