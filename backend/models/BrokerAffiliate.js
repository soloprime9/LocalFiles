import mongoose from 'mongoose';
import slugify from 'slugify';

const brokerAffiliateSchema = new mongoose.Schema({
  name: {
    type: String,
    required: [true, 'Broker name is required'],
    unique: true,
    trim: true
  },
  slug: {
    type: String,
    unique: true,
    lowercase: true
  },
  logo: {
    type: String,
    default: 'https://placehold.co/150x80/1a1a1a/FFF?text=Broker'
  },
  description: {
    type: String,
    required: [true, 'Broker description is required']
  },
  regulatedBy: [{
    type: String // e.g. ["FCA", "ASIC", "CySEC"]
  }],
  licenseNumbers: [{
    type: String
  }],
  assetsCovered: [{
    type: String,
    enum: ['Forex', 'Crypto', 'Stocks', 'Indices', 'Commodities', 'Futures']
  }],
  minDeposit: {
    type: Number,
    required: [true, 'Minimum deposit is required'],
    default: 0
  },
  platforms: [{
    type: String // e.g. ["MT4", "MT5", "cTrader"]
  }],
  spreadType: {
    type: String,
    enum: ['Fixed', 'Variable', 'Raw'],
    default: 'Variable'
  },
  cpaCommission: {
    type: Number, // Commission CPA USD
    default: 0
  },
  revenueShare: {
    type: Number, // Percentage commission
    default: 0
  },
  affiliateUrl: {
    type: String,
    required: [true, 'Affiliate redirect url is required']
  },
  signupUrl: {
    type: String
  },
  rating: {
    type: Number,
    min: 0,
    max: 5,
    default: 0
  },
  trustScore: {
    type: Number,
    min: 0,
    max: 100,
    default: 80
  },
  countryRestrictions: [String],
  isRecommended: {
    type: Boolean,
    default: false
  },
  isFeatured: {
    type: Boolean,
    default: false
  },
  createdAt: {
    type: Date,
    default: Date.now
  }
});

brokerAffiliateSchema.pre('save', function(next) {
  if (this.isModified('name')) {
    this.slug = slugify(this.name, { lower: true, strict: true });
  }
  next();
});

const BrokerAffiliate = mongoose.models.BrokerAffiliate || mongoose.model('BrokerAffiliate', brokerAffiliateSchema);
export default BrokerAffiliate;
