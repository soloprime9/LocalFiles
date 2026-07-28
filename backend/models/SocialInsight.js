import mongoose from 'mongoose';

const socialInsightSchema = new mongoose.Schema({
  title: {
    type: String,
    required: [true, 'Insight title is required'],
    trim: true
  },
  content: {
    type: String,
    required: [true, 'Post content or excerpt is required']
  },
  strategyShared: {
    type: String,
    description: 'Detailed systematic strategy or mathematical logic in markdown'
  },
  platform: {
    type: String,
    required: true,
    enum: ['Twitter/X', 'Reddit', 'Facebook', 'Instagram', 'YouTube']
  },
  author: {
    type: String,
    required: true,
    trim: true
  },
  authorAvatar: {
    type: String,
    default: 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&q=80&w=150'
  },
  sentiment: {
    type: String,
    enum: ['Bullish', 'Neutral', 'Bearish'],
    default: 'Neutral'
  },
  relevanceScore: {
    type: Number,
    min: 0,
    max: 100,
    default: 75
  },
  assetTags: {
    type: [String],
    default: []
  },
  sourceUrl: {
    type: String,
    trim: true
  },
  publishedAt: {
    type: Date,
    default: Date.now
  }
}, {
  timestamps: true
});

const SocialInsight = mongoose.model('SocialInsight', socialInsightSchema);
export default SocialInsight;
