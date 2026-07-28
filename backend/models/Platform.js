import mongoose from 'mongoose';
import slugify from 'slugify';

const platformSchema = new mongoose.Schema({
  name: {
    type: String,
    required: [true, 'Platform name is required'],
    unique: true,
    trim: true,
    maxlength: [100, 'Platform name cannot exceed 100 characters']
  },
  slug: {
    type: String,
    unique: true,
    lowercase: true
  },
  logo: {
    type: String,
    default: 'https://placehold.co/100x100/1a1a1a/FFF?text=Platform'
  },
  description: {
    type: String,
    required: [true, 'Platform description is required']
  },
  userCount: {
    type: String,
    default: '1M+'
  },
  indicatorLanguage: {
    type: String,
    required: [true, 'Coding or scripting language is required (e.g., Pine Script, MQL4, MQL5)']
  },
  affiliateUrl: {
    type: String,
    trim: true
  },
  commissionType: {
    type: String,
    enum: ['recurring_percent', 'cpa', 'revenue_share', 'none'],
    default: 'none'
  },
  commissionValue: {
    type: String,
    default: '0'
  },
  priority: {
    type: Number,
    min: [1, 'Priority cannot be less than 1'],
    max: [6, 'Priority cannot exceed 6'],
    default: 3
  },
  isActive: {
    type: Boolean,
    default: true
  },
  createdAt: {
    type: Date,
    default: Date.now
  }
});

// Auto-generate slug before saving
platformSchema.pre('save', function(next) {
  if (this.isModified('name')) {
    this.slug = slugify(this.name, { lower: true, strict: true });
  }
  next();
});

const Platform = mongoose.models.Platform || mongoose.model('Platform', platformSchema);
export default Platform;
