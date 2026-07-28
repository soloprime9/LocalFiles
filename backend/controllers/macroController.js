import asyncHandler from 'express-async-handler';
import MacroEvent from '../models/MacroEvent.js';

/**
 * @desc    Get macroeconomic events and volatility releases
 * @route   GET /api/v1/macro-calendar
 * @access  Public
 */
export const getMacroCalendar = asyncHandler(async (req, res) => {
  const { impact, currency, affected } = req.query;
  const filter = {};

  if (impact) {
    filter.impact = impact; // Low, Medium, High
  }
  if (currency) {
    filter.currencyAffected = currency.toUpperCase(); // USD, EUR, etc
  }
  if (affected) {
    filter.affectedMarkets = affected; // Forex, Crypto, Stocks
  }

  const events = await MacroEvent.find(filter).sort({ eventTime: 1 });

  res.status(200).json({
    success: true,
    count: events.length,
    data: events
  });
});

/**
 * @desc    Simulate/Create scheduled macroeconomic calendar events
 * @route   POST /api/v1/macro-calendar
 * @access  Public (Simulated admin access)
 */
export const createMacroEvent = asyncHandler(async (req, res) => {
  const { title, country, impact, currencyAffected, affectedMarkets, eventTime, recommendedAction, reportedSentiment, previousValue, forecastValue, actualValue } = req.body;

  if (!title || !impact || !currencyAffected || !eventTime) {
    res.status(400);
    throw new Error('Please fill in required parameters (title, impact, currencyAffected, eventTime)');
  }

  const event = await MacroEvent.create({
    title,
    country: country || 'US',
    impact,
    currencyAffected: currencyAffected.toUpperCase(),
    affectedMarkets: affectedMarkets || ['Forex'],
    eventTime,
    recommendedAction,
    reportedSentiment,
    previousValue,
    forecastValue,
    actualValue
  });

  res.status(201).json({
    success: true,
    message: 'Macroeconomic calendar announcement registered successfully',
    data: event
  });
});
