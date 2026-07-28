import asyncHandler from 'express-async-handler';

/**
 * @desc    Highly precise Position Sizing Evaluator for risk protection management
 * @route   POST /api/v1/calculator/position-size
 * @access  Public
 */
export const calculatePositionSize = asyncHandler(async (req, res) => {
  const {
    accountBalance,
    riskPercent,    // e.g. 1%
    stopLossPips,   // stop loss size in pips (Forex) or points or raw unit differences (Crypto/Indices)
    instrumentType, // 'Forex', 'Crypto', 'Stocks', 'Indices'
    pipValue,       // Optional: explicit pip value relative to quote currecy
    symbol          // e.g. "EURUSD", "BTCUSDT"
  } = req.body;

  if (!accountBalance || !riskPercent || !stopLossPips || !instrumentType) {
    res.status(400);
    throw new Error('Please include vital criteria (accountBalance, riskPercent, stopLossPips, instrumentType)');
  }

  const cashRisk = accountBalance * (riskPercent / 100);
  let units = 0;
  let standardLots = 0;
  let explanation = '';

  if (instrumentType === 'Forex') {
    // Standard pip sizing rules: 1 standard lot is 100,000 units. 1 pip = $10 on a standard lot of standard pairs like EURUSD.
    // Standard pip values default to 10 USD per lot for most key pairs when USD is the quote currency.
    const effectivePipVal = pipValue || 10; // default 10 USD per standard lot
    standardLots = cashRisk / (stopLossPips * effectivePipVal);
    units = standardLots * 100000;
    explanation = 'Calculated standard lots where 1 standard lot equals 100,000 base currency units.';
  } else if (instrumentType === 'Crypto') {
    // For cryptocurrencies, units correspond to raw tokens e.g. 1.25 BTC
    // Stop loss size is raw price points (difference in USD e.g. $1000 stop loss range)
    units = cashRisk / stopLossPips;
    explanation = 'Crypto position size calculations based on raw asset unit/token pricing points.';
  } else if (instrumentType === 'Stocks') {
    // For equities, units correspond directly to share counts
    // Stop loss is raw share price difference (e.g. standard stock price decreases $5)
    units = cashRisk / stopLossPips;
    explanation = 'Stock size determines share volume purchase targets directly.';
  } else if (instrumentType === 'Indices') {
    // Dynamic index sizes based on points risk (e.g. US30 index points, standard contract values)
    const factor = pipValue || 1.0; // point value multiplier
    units = cashRisk / (stopLossPips * factor);
    explanation = 'Index point valuation variables map directly according to specific broker terminal specifications.';
  }

  res.status(200).json({
    success: true,
    data: {
      instrumentType,
      symbol: symbol || 'Generic Asset',
      accountBalance,
      riskPercent,
      cashRisk: parseFloat(cashRisk.toFixed(2)),
      stopLossPips,
      calculatedUnits: parseFloat(units.toFixed(6)),
      calculatedLots: instrumentType === 'Forex' ? parseFloat(standardLots.toFixed(4)) : undefined,
      explanation
    }
  });
});

/**
 * @desc    Get dynamic multi-tier Martingale & DCA step sizes for trading bots
 * @route   POST /api/v1/calculator/dca-presets
 * @access  Public
 */
export const calculateDcaGrid = asyncHandler(async (req, res) => {
  const {
    initialBaseOrder, // e.g. $10
    stepCount,        // e.g. 5 steps
    martingaleMultiplier, // e.g. 1.5x, 2.0x
    priceDeviationPercent, // e.g. 1.2% per safety order
    stepBiasMultiplier      // e.g. 1.1x scaling for wider deviation
  } = req.body;

  if (!initialBaseOrder || !stepCount || !martingaleMultiplier || !priceDeviationPercent) {
    res.status(400);
    throw new Error('Please include vital parameters (initialBaseOrder, stepCount, martingaleMultiplier, priceDeviationPercent)');
  }

  const dcaSteps = [];
  let currentOrderVal = initialBaseOrder;
  let cumulativeValue = initialBaseOrder;
  let targetDeviation = 0;
  let activeBias = stepBiasMultiplier || 1.0;

  dcaSteps.push({
    orderIndex: 0,
    type: 'Base Order',
    requiredMargin: parseFloat(initialBaseOrder.toFixed(2)),
    cumulativeMargin: parseFloat(initialBaseOrder.toFixed(2)),
    entryDeviationPercent: 0
  });

  for (let i = 1; i <= stepCount; i++) {
    currentOrderVal = currentOrderVal * martingaleMultiplier;
    cumulativeValue += currentOrderVal;
    
    // Increment deviations
    const currentDeviationStep = priceDeviationPercent * Math.pow(activeBias, i - 1);
    targetDeviation += currentDeviationStep;

    dcaSteps.push({
      orderIndex: i,
      type: `Safety Order #${i}`,
      requiredMargin: parseFloat(currentOrderVal.toFixed(2)),
      cumulativeMargin: parseFloat(cumulativeValue.toFixed(2)),
      entryDeviationPercent: parseFloat(targetDeviation.toFixed(3))
    });
  }

  res.status(200).json({
    success: true,
    data: {
      initialBaseOrder,
      stepCount,
      martingaleMultiplier,
      totalCapitalRequired: parseFloat(cumulativeValue.toFixed(2)),
      maxCoveragePercent: parseFloat(targetDeviation.toFixed(3)),
      steps: dcaSteps
    }
  });
});
