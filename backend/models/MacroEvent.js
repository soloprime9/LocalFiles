import mongoose from 'mongoose';

const macroEventSchema = new mongoose.Schema({
  title: {
    type: String,
    required: [true, 'Event title is required'],
    trim: true
  },
  country: {
    type: String,
    default: 'US'
  },
  impact: {
    type: String,
    enum: ['Low', 'Medium', 'High'],
    required: true
  },
  previousValue: String,
  forecastValue: String,
  actualValue: String,
  currencyAffected: {
    type: String, // e.g. "USD", "EUR", "JPY"
    uppercase: true,
    required: true
  },
  affectedMarkets: [{
    type: String,
    enum: ['Forex', 'Crypto', 'Stocks', 'Gold', 'Indices']
  }],
  eventTime: {
    type: Date,
    required: [true, 'Calendar event execution time is required']
  },
  recommendedAction: {
    type: String, // e.g. "Pause scalp bots 30m before and after event"
    default: 'Monitor volatility standard thresholds'
  },
  reportedSentiment: {
    type: String,
    enum: ['Hawkish', 'Dovish', 'Neutral', 'Inflationary', 'Deflationary'],
    default: 'Neutral'
  }
}, {
  timestamps: true
});

macroEventSchema.index({ eventTime: -1 });

const MacroEvent = mongoose.models.MacroEvent || mongoose.model('MacroEvent', macroEventSchema);
export default MacroEvent;
