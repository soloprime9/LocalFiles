import mongoose from 'mongoose';

const backtestReportSchema = new mongoose.Schema({
  indicatorId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Indicator',
    required: [true, 'Associated indicator is required']
  },
  testerName: {
    type: String,
    required: [true, 'Tester name/alias is required']
  },
  testerType: {
    type: String,
    enum: ['Beginner', 'Intermediate', 'Pro', 'Quantitative Developer'],
    default: 'Intermediate'
  },
  timeframe: {
    type: String,
    required: [true, 'Testing timeframe is required']
  },
  marketSymbol: {
    type: String,
    uppercase: true,
    required: [true, 'Tested instrument/symbol is required']
  },
  testPeriod: {
    type: String, // e.g., "Jan 1, 2024 - Jun 1, 2026"
    required: [true, 'Testing range period is required']
  },
  metrics: {
    netProfitPercent: { type: Number, required: true },
    maxDrawdownPercent: { type: Number, required: true },
    profitFactor: { type: Number, required: true },
    winRatePercent: { type: Number, required: true, min: 0, max: 100 },
    totalTrades: { type: Number, required: true, min: 1 },
    sharpeRatio: { type: Number },
    recoveryFactor: { type: Number }
  },
  dataSource: {
    type: String,
    enum: ['TradingView Strategy Tester', 'MetaTrader Backtest Log', 'Custom Python Framework', 'Manual Simulation'],
    required: true
  },
  verifiedWithLogs: {
    type: Boolean,
    default: false
  },
  tradeHistoryFileUrl: {
    type: String // Optional link to raw CSV/JSON logs uploaded by users
  },
  userReviewNotes: {
    type: String,
    maxlength: [1000, 'Notes cannot exceed 1000 characters']
  },
  discrepancyFlag: {
    type: Boolean,
    default: false // Set to true if community reports huge difference compared to author claims
  },
  discrepancyReason: String,
  upvotes: { type: Number, default: 0 }
}, {
  timestamps: true
});

backtestReportSchema.index({ indicatorId: 1, 'metrics.profitFactor': -1 });

const BacktestReport = mongoose.models.BacktestReport || mongoose.model('BacktestReport', backtestReportSchema);
export default BacktestReport;
