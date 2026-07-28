import mongoose from 'mongoose';

const signalSchema = new mongoose.Schema({
  name: {
    type: String,
    required: [true, 'Signal feed or provider name is required'],
    trim: true
  },
  provider: {
    type: String,
    required: [true, 'Provider name or signature is required'],
    trim: true
  },
  indicatorRef: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Indicator'
  },
  asset: {
    type: String,
    required: [true, 'Asset pair is required (e.g., BTC/USDT, EUR/USD)'],
    trim: true,
    uppercase: true
  },
  direction: {
    type: String,
    enum: ['Buy', 'Sell', 'Neutral'],
    required: true
  },
  entry: {
    type: Number,
    required: [true, 'Entry trigger price is required']
  },
  stopLoss: {
    type: Number,
    required: [true, 'Stop Loss price is required']
  },
  takeProfit1: {
    type: Number,
    required: [true, 'Take Profit 1 target is required']
  },
  takeProfit2: {
    type: Number
  },
  takeProfit3: {
    type: Number
  },
  timeframe: {
    type: String,
    required: [true, 'Signal timeframe is required (e.g., 15m, 1h, 4h)']
  },
  signalType: {
    type: String,
    enum: ['Technical', 'Fundamental', 'AI', 'Combined'],
    default: 'Technical'
  },
  deliveryMethod: {
    type: String,
    enum: ['Telegram', 'Email', 'Discord', 'WhatsApp', 'App', 'SMS'],
    default: 'Telegram'
  },
  isActive: {
    type: Boolean,
    default: true
  },
  winRateHistoric: {
    type: Number,
    min: 0,
    max: 100,
    default: 0
  },
  totalSignalsIssued: {
    type: Number,
    default: 0
  },
  successfulSignals: {
    type: Number,
    default: 0
  },
  price: {
    type: Number,
    default: 0 // Free or has a premium subscription costs
  },
  affiliateUrl: {
    type: String
  }
}, {
  timestamps: true
});

signalSchema.index({ asset: 1, isActive: 1 });
signalSchema.index({ provider: 1 });

const Signal = mongoose.models.Signal || mongoose.model('Signal', signalSchema);
export default Signal;
