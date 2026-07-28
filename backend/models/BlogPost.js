import mongoose from 'mongoose';
import slugify from 'slugify';

const blogPostSchema = new mongoose.Schema({
  title: {
    type: String,
    required: [true, 'Blog post title is required'],
    trim: true,
    unique: true,
    maxlength: [150, 'Title cannot exceed 150 characters']
  },
  slug: {
    type: String,
    unique: true,
    lowercase: true
  },
  excerpt: {
    type: String,
    required: [true, 'Summary/Excerpt is required'],
    maxlength: [300, 'Excerpt cannot exceed 300 characters']
  },
  content: {
    type: String,
    required: [true, 'Markdown content of the post is required']
  },
  author: {
    type: String,
    required: [true, 'Author is required'],
    default: 'IndicatorHub Team'
  },
  coverImage: {
    type: String,
    default: 'https://placehold.co/800x400/1a1a1a/F59E0B?text=Blog+Cover'
  },
  tags: [String],
  category: {
    type: String,
    required: [true, 'Category is required'],
    default: 'General'
  },
  relatedIndicators: [{
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Indicator'
  }],
  isFeatured: {
    type: Boolean,
    default: false
  },
  views: {
    type: Number,
    default: 0
  },
  readTime: {
    type: Number, // In minutes
    default: 5
  },
  status: {
    type: String,
    enum: ['draft', 'published'],
    default: 'draft'
  },
  publishedAt: {
    type: Date
  }
}, {
  timestamps: true
});

blogPostSchema.pre('save', function(next) {
  if (this.isModified('title')) {
    this.slug = slugify(this.title, { lower: true, strict: true });
  }
  
  if (this.status === 'published' && !this.publishedAt) {
    this.publishedAt = new Date();
  }
  
  next();
});

const BlogPost = mongoose.models.BlogPost || mongoose.model('BlogPost', blogPostSchema);
export default BlogPost;
