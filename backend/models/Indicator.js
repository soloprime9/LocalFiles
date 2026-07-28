import mongoose from 'mongoose';
import slugify from 'slugify';

const faqSchema = new mongoose.Schema({
  question: { type: String, required: true },
  answer: { type: String, required: true }
});

const backtestSchema = new mongoose.Schema({
  winRate: { type: Number, min: 0, max: 100, default: 0 },
  sharpeRatio: { type: Number, default: 0 },
  sortinoRatio: { type: Number, default: 0 },
  maxDrawdown: { type: Number, min: 0, max: 100, default: 0 }, // Percent
  profitFactor: { type: Number, default: 1 },
  totalTrades: { type: Number, default: 0 },
  avgTradesPerMonth: { type: Number, default: 0 },
  backtestPeriod: { type: String, default: 'N/A' },
  backtestCapital: { type: Number, default: 0 },
  auditStatus: {
    type: String,
    enum: ['Verified', 'Suspicious', 'Unaudited'],
    default: 'Unaudited'
  },
  auditNotes: { type: String },
  forwardTestActive: { type: Boolean, default: false }
});

const compatibilitySchema = new mongoose.Schema({
  tradingViewVersion: { type: String },
  mtVersion: { type: String },
  minCapital: { type: Number, default: 0 },
  requiresBroker: { type: Boolean, default: false },
  brokerRecommended: { type: String }
});

const indicatorSchema = new mongoose.Schema({
  name: {
    type: String,
    required: [true, 'Indicator name is required'],
    trim: true,
    unique: true,
    maxlength: [100, 'Name cannot exceed 100 characters']
  },
  slug: {
    type: String,
    unique: true,
    lowercase: true
  },
  listingType: {
    type: String,
    required: [true, 'Listing type is required'],
    enum: [
      'Indicator', 'EA', 'Bot', 'Signal', 'Strategy', 'Screener', 
      'Script', 'Alert', 'CopyTrading', 'Template', 'Course'
    ]
  },
  category: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Category',
    required: [true, 'Category reference is required']
  },
  platform: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Platform',
    required: [true, 'Platform reference is required']
  },
  description: {
    type: String,
    required: [true, 'Short description is required'],
    maxlength: [300, 'Short description cannot exceed 300 characters']
  },
  longDescription: {
    type: String,
    required: [true, 'Long description is required']
  },
  assetClass: [{
    type: String,
    enum: [
      'Crypto', 'Forex', 'Stocks', 'Indices', 'Gold', 'Silver', 
      'Oil', 'Commodities', 'Futures', 'Options', 'ETFs'
    ]
  }],
  strategyType: [{
    type: String,
    enum: [
      'Trend', 'Momentum', 'Reversal', 'Scalping', 'Day Trading', 
      'Swing', 'Position', 'Breakout', 'Bounce', 'Volume', 
      'Volatility', 'Mean Reversion', 'Smart Money', 'Price Action', 
      'Harmonic', 'Grid', 'DCA', 'Arbitrage'
    ]
  }],
  timeframes: [{
    type: String,
    enum: ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1', 'W1', 'MN']
  }],
  difficulty: {
    type: String,
    enum: ['Beginner', 'Intermediate', 'Advanced', 'Expert'],
    default: 'Intermediate'
  },
  price: {
    type: Number,
    required: [true, 'Price is required'],
    default: 0
  },
  pricingModel: {
    type: String,
    enum: ['Free', 'One-time', 'Monthly', 'Yearly', 'Freemium', 'Rental'],
    default: 'Free'
  },
  isFree: {
    type: Boolean,
    default: false
  },
  isPremiumListing: {
    type: Boolean,
    default: false
  },
  isFeatured: {
    type: Boolean,
    default: false
  },
  isVerified: {
    type: Boolean,
    default: false
  },
  isScamFlagged: {
    type: Boolean,
    default: false
  },
  scamReason: {
    type: String
  },
  trendingScore: {
    type: Number,
    default: 0
  },
  weeklyViews: {
    type: Number,
    default: 0
  },
  totalViews: {
    type: Number,
    default: 0
  },
  weeklyLikes: {
    type: Number,
    default: 0
  },
  totalLikes: {
    type: Number,
    default: 0
  },
  tags: [String],
  author: {
    type: String,
    required: [true, 'Author name/team is required']
  },
  authorUrl: { type: String },
  externalUrl: { type: String },
  affiliateUrl: { type: String },
  imageUrl: {
    type: String,
    default: 'https://placehold.co/800x400/1a1a1a/F59E0B?text=Indicator'
  },
  screenshots: [String],
  videoUrl: { type: String },
  demoUrl: { type: String },
  rating: {
    type: Number,
    min: 0,
    max: 5,
    default: 0
  },
  totalReviews: {
    type: Number,
    default: 0
  },
  trustScore: {
    type: Number,
    min: 0,
    max: 100,
    default: 0
  },
  backtestData: {
    type: backtestSchema,
    default: () => ({})
  },
  compatibility: {
    type: compatibilitySchema,
    default: () => ({})
  },
  pros: {
    type: [String],
    validate: [val => val.length <= 5, 'Pros cannot exceed 5 items']
  },
  cons: {
    type: [String],
    validate: [val => val.length <= 5, 'Cons cannot exceed 5 items']
  },
  faqs: [faqSchema],
  relatedIds: [{
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Indicator'
  }],
  submittedBy: {
    type: String,
    required: [true, 'Submitter email is required']
  },
  adminNotes: { type: String },
  status: {
    type: String,
    enum: ['pending', 'active', 'rejected'],
    default: 'active'
  }
}, {
  timestamps: true
});

// Indexes for super-fast searching & filtered directory queries
indicatorSchema.index({ name: 'text', description: 'text', tags: 'text' });
// indicatorSchema.index({ slug: 1 });
indicatorSchema.index({ isFeatured: 1, trendingScore: -1 });
indicatorSchema.index({ category: 1, platform: 1, listingType: 1 });

// Pre-save validations, slugification, and calculation of TrustScore
indicatorSchema.pre('save', function(next) {
  // Auto slugify name
  if (this.isModified('name')) {
    this.slug = slugify(this.name, { lower: true, strict: true });
  }

  // Force isFree boolean synchronization with underlying price state
  if (this.isModified('price')) {
    this.isFree = this.price === 0;
  }

  // Auto-set pricing model if price is zero
  if (this.price === 0) {
    this.pricingModel = 'Free';
  }

  // Calculate TrustScore algorithm
  // Algorithmic weights:
  // - Rating contribution: up to 75 points (rating * 15)
  // - Platform Verification contribution: 20 points
  // - Audited Backtest confirmation: 25 points
  // - Moderate item volume (reviews > 5): 10 points
  // - High item volume (reviews > 20): 10 points
  // - Scam Penalization check: Up to 20 points if NOT flagged
  
  const ratingContribution = (this.rating || 0) * 15;
  const verificationBonus = this.isVerified ? 20 : 0;
  const auditBonus = (this.backtestData && this.backtestData.auditStatus === 'Verified') ? 25 : 0;
  const minorReviewBonus = (this.totalReviews > 5) ? 10 : 0;
  const majorReviewBonus = (this.totalReviews > 20) ? 10 : 0;
  const antiScamBonus = !this.isScamFlagged ? 20 : 0;

  this.trustScore = Math.min(
    100,
    Math.max(0, Math.round(ratingContribution + verificationBonus + auditBonus + minorReviewBonus + majorReviewBonus + antiScamBonus))
  );

  next();
});

const Indicator = mongoose.models.Indicator || mongoose.model('Indicator', indicatorSchema);
export default Indicator;
