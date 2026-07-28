import mongoose from 'mongoose';

const reviewSchema = new mongoose.Schema({
  indicatorId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Indicator',
    required: [true, 'Review must belong to an indicator']
  },
  reviewerName: {
    type: String,
    required: [true, 'Please provide your name or trading handle'],
    trim: true
  },
  reviewerEmail: {
    type: String,
    trim: true
  },
  reviewerType: {
    type: String,
    enum: ['Beginner', 'Intermediate', 'Pro', 'Institutional'],
    default: 'Intermediate'
  },
  rating: {
    type: Number,
    required: [true, 'Please rate from 1 to 5 stars'],
    min: 1,
    max: 5
  },
  title: {
    type: String,
    required: [true, 'Review headline/title is required'],
    trim: true,
    maxlength: [100, 'Title cannot exceed 100 characters']
  },
  body: {
    type: String,
    required: [true, 'Review text feedback is required'],
    minlength: [50, 'Review feedback must contain at least 50 characters to prevent spam']
  },
  tradingPeriod: {
    type: String,
    placeholder: 'e.g. 45 days, 6 months'
  },
  assetTraded: {
    type: String,
    placeholder: 'e.g. BTC/USDT, EUR/USD'
  },
  timeframeUsed: {
    type: String,
    placeholder: 'e.g. H1, D1, 15m'
  },
  profitableForReviewer: {
    type: Boolean,
    default: true
  },
  wouldRecommend: {
    type: Boolean,
    default: true
  },
  helpful: {
    type: Number,
    default: 0
  },
  notHelpful: {
    type: Number,
    default: 0
  },
  verified: {
    type: Boolean,
    default: false
  },
  isScam: {
    type: Boolean,
    default: false
  },
  platform: {
    type: String
  },
  createdAt: {
    type: Date,
    default: Date.now
  }
});

// Compound index to prevent double review spam from same email on one indicator
reviewSchema.index({ indicatorId: 1, reviewerEmail: 1 }, { unique: true, sparse: true });
reviewSchema.index({ indicatorId: 1, helpful: -1 });

// Static method to calculate average rating and update on parent indicator
reviewSchema.statics.calculateAverageRating = async function(indicatorId) {
  const stats = await this.aggregate([
    {
      $match: { indicatorId }
    },
    {
      $group: {
        _id: '$indicatorId',
        nRatings: { $sum: 1 },
        avgRating: { $avg: '$rating' }
      }
    }
  ]);

  if (stats.length > 0) {
    // Dynamic recalculation directly on the parent
    const Indicator = mongoose.model('Indicator');
    const ind = await Indicator.findById(indicatorId);
    if (ind) {
      ind.rating = Math.round(stats[0].avgRating * 10) / 10;
      ind.totalReviews = stats[0].nRatings;
      await ind.save();
    }
  } else {
    const Indicator = mongoose.model('Indicator');
    const ind = await Indicator.findById(indicatorId);
    if (ind) {
      ind.rating = 0;
      ind.totalReviews = 0;
      await ind.save();
    }
  }
};

// Call calculateAverageRating after save
reviewSchema.post('save', async function() {
  await this.constructor.calculateAverageRating(this.indicatorId);
});

// Call calculateAverageRating after delete/remove triggers
reviewSchema.post('save', async function() {
  await this.constructor.calculateAverageRating(this.indicatorId);
});

const Review = mongoose.models.Review || mongoose.model('Review', reviewSchema);
export default Review;
