import mongoose from 'mongoose';

const submitRequestSchema = new mongoose.Schema({
  submitterName: {
    type: String,
    required: [true, 'Submitter name is required'],
    trim: true
  },
  submitterEmail: {
    type: String,
    required: [true, 'Contact email address is required'],
    trim: true,
    lowercase: true
  },
  submitterWebsite: {
    type: String,
    trim: true
  },
  toolName: {
    type: String,
    required: [true, 'Trading tool name is required'],
    trim: true
  },
  toolUrl: {
    type: String,
    required: [true, 'Direct product page URL is required'],
    trim: true
  },
  listingType: {
    type: String,
    required: [true, 'Tool listing type is required'],
    enum: [
      'Indicator', 'EA', 'Bot', 'Signal', 'Strategy', 'Screener', 
      'Script', 'Alert', 'CopyTrading', 'Template', 'Course'
    ]
  },
  platform: {
    type: String,
    required: [true, 'Trading platform required (e.g. TradingView, MT4)']
  },
  price: {
    type: Number,
    default: 0
  },
  description: {
    type: String,
    required: [true, 'Brief explanation is required']
  },
  backtestProofUrl: {
    type: String,
    trim: true
  },
  contactMessage: {
    type: String
  },
  status: {
    type: String,
    enum: ['pending', 'approved', 'rejected'],
    default: 'pending'
  },
  adminReply: {
    type: String
  },
  createdAt: {
    type: Date,
    default: Date.now
  }
});

const SubmitRequest = mongoose.models.SubmitRequest || mongoose.model('SubmitRequest', submitRequestSchema);
export default SubmitRequest;
