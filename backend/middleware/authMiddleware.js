import jwt from 'jsonwebtoken';
import asyncHandler from 'express-async-handler';
import { User } from '../models/index.js';

export const protect = asyncHandler(async (req, res, next) => {
  let token;

  if (
    req.headers.authorization &&
    req.headers.authorization.startsWith('Bearer')
  ) {
    try {
      token = req.headers.authorization.split(' ')[1];

      // Decode token
      const decoded = jwt.verify(token, process.env.JWT_SECRET || 'falconspido_jwt_secure_key_2026');

      // Get user from database without password field
      req.user = await User.findById(decoded.id).select('-password');

      if (!req.user) {
        res.status(401);
        throw new Error('User associated with this credential no longer exists.');
      }

      next();
    } catch (error) {
      console.error('[JWT Verification Failure]:', error.message);
      res.status(401);
      throw new Error('Not authorized, token failed verification or expired.');
    }
  }

  if (!token) {
    res.status(401);
    throw new Error('Not authorized, no authorization header with Bearer token provided.');
  }
});

// Admin status guard
export const admin = (req, res, next) => {
  if (req.user && req.user.role === 'admin') {
    next();
  } else {
    res.status(403);
    throw new Error('Not authorized as administrative moderator.');
  }
};
