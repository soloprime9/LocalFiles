import mongoose from 'mongoose';

const configPresetSchema = new mongoose.Schema({
  indicatorId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Indicator',
    required: [true, 'Associated indicator is required']
  },
  title: {
    type: String,
    required: [true, 'Preset/Settings title is required'],
    trim: true,
    maxlength: [100, 'Title cannot exceed 100 characters']
  },
  description: {
    type: String,
    maxlength: [300, 'Description cannot exceed 300 characters']
  },
  assetClass: {
    type: String,
    required: true,
    enum: ['Crypto', 'Forex', 'Stocks', 'Indices', 'Commodities', 'Futures', 'Options']
  },
  symbol: {
    type: String,
    required: [true, 'Target trading symbol is required'], // e.g. "BTCUSDT", "EURUSD", "XAUUSD"
    uppercase: true,
    trim: true
  },
  timeframe: {
    type: String,
    required: [true, 'Target timeframe is required'], // e.g. "M5", "M15", "H1", "D1"
    trim: true
  },
  parameters: {
    type: Map,
    of: String,
    required: [true, 'Preset key-value parameters are required'] // e.g. { "Length": "14", "Multiplier": "2.0", "Source": "Close" }
  },
  backtestResults: {
    winRate: { type: Number, min: 0, max: 100 },
    profitFactor: { type: Number, min: 0 },
    maxDrawdown: { type: Number, min: 0 },
    totalTrades: { type: Number, min: 1 },
    period: { type: String } // e.g. "6 Months", "1 Year"
  },
  author: {
    type: String,
    default: 'Retail Quant'
  },
  votes: {
    upvotes: { type: Number, default: 0 },
    downvotes: { type: Number, default: 0 }
  },
  isVerifiedByStaff: {
    type: Boolean,
    default: false
  }
}, {
  timestamps: true
});

configPresetSchema.index({ indicatorId: 1, symbol: 1 });
configPresetSchema.index({ 'votes.upvotes': -1 });

const ConfigPreset = mongoose.models.ConfigPreset || mongoose.model('ConfigPreset', configPresetSchema);
export default ConfigPreset;
