import asyncHandler from 'express-async-handler';
import BacktestReport from '../models/BacktestReport.js';
import Indicator from '../models/Indicator.js';

/**
 * @desc    Get structured backtest reports submitted by users for an indicator
 * @route   GET /api/v1/backtest-reports/indicator/:indicatorId
 * @access  Public
 */
export const getBacktestReports = asyncHandler(async (req, res) => {
  const { indicatorId } = req.params;

  const reports = await BacktestReport.find({ indicatorId }).sort({ createdAt: -1 });

  res.status(200).json({
    success: true,
    count: reports.length,
    data: reports
  });
});

/**
 * @desc    Submit user backtest dataset logs for comparative auditing
 * @route   POST /api/v1/backtest-reports
 * @access  Public
 */
export const submitBacktestReport = asyncHandler(async (req, res) => {
  const {
    indicatorId,
    testerName,
    testerType,
    timeframe,
    marketSymbol,
    testPeriod,
    metrics,
    dataSource,
    userReviewNotes,
    tradeHistoryFileUrl
  } = req.body;

  if (!indicatorId || !testerName || !timeframe || !marketSymbol || !testPeriod || !metrics || !dataSource) {
    res.status(400);
    throw new Error('Please fill all required verification parameters.');
  }

  // Fetch parent indicator metadata to run automatic discrepancy audits
  const parentIndicator = await Indicator.findById(indicatorId);
  if (!parentIndicator) {
    res.status(404);
    throw new Error('Associated indicator listing not found.');
  }

  // Automatic programmatic discrepancy audits:
  // If user-determined win rate is 15%+ lower than author claims, or max drawdown is 12%+ higher than author's listed limits, we trigger a discrepancy warning automatically.
  let discrepancyFlag = false;
  let discrepancyReason = '';

  const authorWinRate = parentIndicator.backtestData ? parentIndicator.backtestData.winRate : null;
  const authorDrawdown = parentIndicator.backtestData ? parentIndicator.backtestData.maxDrawdown : null;

  if (authorWinRate && (authorWinRate - metrics.winRatePercent >= 15)) {
    discrepancyFlag = true;
    discrepancyReason += `Reported winrate (${metrics.winRatePercent}%) is extremely low compared to author's configured claim (${authorWinRate}%). `;
  }

  if (authorDrawdown && (metrics.maxDrawdownPercent - authorDrawdown >= 12)) {
    discrepancyFlag = true;
    discrepancyReason += `Reported max drawdown (${metrics.maxDrawdownPercent}%) exceeds author's limit criteria (${authorDrawdown}%). `;
  }

  const report = await BacktestReport.create({
    indicatorId,
    testerName,
    testerType: testerType || 'Intermediate',
    timeframe,
    marketSymbol: marketSymbol.toUpperCase(),
    testPeriod,
    metrics,
    dataSource,
    userReviewNotes,
    tradeHistoryFileUrl,
    discrepancyFlag,
    discrepancyReason
  });

  // Increment indicator views/counts due to engagement
  parentIndicator.totalViews += 1;
  await parentIndicator.save();

  res.status(201).json({
    success: true,
    message: discrepancyFlag 
      ? 'Verification dataset compiled successfully. Warning: Discrepancy detected with public material.' 
      : 'User verified backtest audit successfully submitted to verification records.',
    data: report
  });
});
