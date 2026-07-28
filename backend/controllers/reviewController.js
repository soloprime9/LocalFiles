import asyncHandler from 'express-async-handler';
import { Review, Indicator } from '../models/index.js';

/**
 * @desc    Get paginated reviews for a specific indicator with helpfulness rankings
 * @route   GET /api/v1/reviews/indicator/:indicatorId
 * @access  Public
 */
export const getReviewsByIndicator = asyncHandler(async (req, res) => {
  const { indicatorId } = req.params;
  const { page = 1, limit = 5 } = req.query;

  const skip = (parseInt(page) - 1) * parseInt(limit);

  const reviews = await Review.find({ indicatorId })
    .sort({ helpful: -1, createdAt: -1 })
    .skip(skip)
    .limit(parseInt(limit));

  const total = await Review.countDocuments({ indicatorId });

  // Compute rating breakdown star distributions
  const distributions = await Review.aggregate([
    { $match: { indicatorId: new mongoose.Types.ObjectId(indicatorId) } },
    { $group: { _id: '$rating', count: { $sum: 1 } } }
  ]);

  const ratingBreakdown = { 5: 0, 4: 0, 3: 0, 2: 0, 1: 0 };
  distributions.forEach(d => {
    if (ratingBreakdown[d._id] !== undefined) {
      ratingBreakdown[d._id] = d.count;
    }
  });

  const parent = await Indicator.findById(indicatorId);

  res.status(200).json({
    success: true,
    reviews,
    total,
    page: parseInt(page),
    pages: Math.ceil(total / parseInt(limit)),
    avgRating: parent ? parent.rating : 0,
    ratingBreakdown
  });
});

/**
 * @desc    Write an objective trading feedback review on a listed strategy
 * @route   POST /api/v1/reviews
 * @access  Public
 */
export const createReview = asyncHandler(async (req, res) => {
  const { indicatorId, reviewerName, reviewerEmail, rating, title, body } = req.body;

  if (!indicatorId || !reviewerName || !rating || !title || !body) {
    return res.status(400).json({ success: false, error: 'Please submit all required review fields.' });
  }

  if (rating < 1 || rating > 5) {
    return res.status(400).json({ success: false, error: 'Rating must be an integer between 1 and 5' });
  }

  if (body.length < 50) {
    return res.status(400).json({ success: false, error: 'Please write at least 50 characters of constructive trading feedback.' });
  }

  // Check if target indicator exists
  const target = await Indicator.findById(indicatorId);
  if (!target) {
    return res.status(404).json({ success: false, error: 'The requested listing does not exist' });
  }

  // Review submission creation (Compound index prevents duplicate review spam via mongoose)
  try {
    const reviewObj = await Review.create(req.body);
    res.status(201).json({ success: true, data: reviewObj });
  } catch (err) {
    if (err.code === 11000) {
      return res.status(400).json({ success: false, error: 'You have already submitted a review for this trading tool!' });
    }
    throw err;
  }
});

/**
 * @desc    Cast helpful vote on a review card
 * @route   PATCH /api/v1/reviews/:id/helpful
 * @access  Public
 */
export const markHelpful = asyncHandler(async (req, res) => {
  const reviewObj = await Review.findById(req.params.id);
  if (!reviewObj) {
    return res.status(404).json({ success: false, error: 'Review card not found' });
  }

  reviewObj.helpful += 1;
  await reviewObj.save();

  res.status(200).json({ success: true, helpful: reviewObj.helpful });
});

/**
 * @desc    Cast not-helpful downvote on a review card
 * @route   PATCH /api/v1/reviews/:id/not-helpful
 * @access  Public
 */
export const markNotHelpful = asyncHandler(async (req, res) => {
  const reviewObj = await Review.findById(req.params.id);
  if (!reviewObj) {
    return res.status(404).json({ success: false, error: 'Review card not found' });
  }

  reviewObj.notHelpful += 1;
  await reviewObj.save();

  res.status(200).json({ success: true, notHelpful: reviewObj.notHelpful });
});
import mongoose from 'mongoose';
