import React, { useState, useEffect } from 'react';
import { apiService } from '../utils/api';
import { Badge } from '../components/ui/Badge';
import { setSeo } from '../utils/seo';
import { 
  Calculator, 
  ChevronRight, 
  TrendingUp, 
  Percent, 
  HelpCircle, 
  ShieldCheck, 
  ShieldAlert 
} from 'lucide-react';

export const Calculators = () => {
  // Sizer States
  const [balance, setBalance] = useState(10000);
  const [riskPercent, setRiskPercent] = useState(1.5);
  const [stopLoss, setStopLoss] = useState(30);
  const [instrument, setInstrument] = useState('Forex');
  const [sizeRes, setSizeRes] = useState(null);
  const [sizeLoading, setSizeLoading] = useState(false);

  // DCA Grid States
  const [dcaBase, setDcaBase] = useState(100);
  const [dcaSteps, setDcaSteps] = useState(7);
  const [dcaMultiplier, setDcaMultiplier] = useState(1.5);
  const [dcaDeviation, setDcaDeviation] = useState(1.5);
  const [gridRes, setGridRes] = useState(null);
  const [gridLoading, setGridLoading] = useState(false);

  useEffect(() => {
    setSeo({
  title: `${fetchedInd.name} — Review, Parameters, and Audits | FalconSpido`,
  description: fetchedInd.description || `${fetchedInd.name} reviews, parameters, and trust score on FalconSpido.`,
  path: `/indicators/${fetchedInd.slug}`
});
    // Trigger initial default calculations
    handleSizerCalc();
    handleGridCalc();
  }, []);

  const handleSizerCalc = async (e) => {
    if (e) e.preventDefault();
    setSizeLoading(true);
    try {
      const res = await apiService.calculatePositionSize({
        accountBalance: balance,
        riskPercent,
        stopLossPips: stopLoss,
        instrumentType: instrument,
        pipValue: 10 // default standard USD valuation
      });
      if (res?.success) {
        setSizeRes(res.data);
      }
    } catch (err) {
      console.error('Sizer calculation error:', err);
    } finally {
      setSizeLoading(false);
    }
  };

  const handleGridCalc = async (e) => {
    if (e) e.preventDefault();
    setGridLoading(true);
    try {
      const res = await apiService.calculateDcaGrid({
        initialBaseOrder: dcaBase,
        stepCount: dcaSteps,
        martingaleMultiplier: dcaMultiplier,
        priceDeviationPercent: dcaDeviation
      });
      if (res?.success) {
        setGridRes(res.data);
      }
    } catch (err) {
      console.error('Grid calculation error:', err);
    } finally {
      setGridLoading(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-12">
      
      {/* Title */}
      <div className="space-y-1">
        <span className="text-[10px] text-amber-500 uppercase tracking-widest font-extrabold flex items-center space-x-1">
          <Calculator className="h-4.5 w-4.5 text-amber-500" />
          <span>QUANT CONTROL PANEL</span>
        </span>
        <h1 className="text-xl sm:text-3xl font-black text-white">Position Sizing & DCA Risk Calculators</h1>
        <p className="text-xs text-slate-400 max-w-xl">
          Apply dynamic math ratios to protect your trading capital. Ensure precise contract sizes and construct multi-tier Martingale architectures before launching bots.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
        
        {/* Module 1: Position Risk Calculator */}
        <div className="bg-[#08080d] border border-white/5 rounded-2xl p-6 space-y-6 shadow-xl">
          <h3 className="text-base font-extrabold text-white uppercase tracking-wider flex items-center space-x-2">
            <Percent className="h-4.5 w-4.5 text-amber-500" />
            <span>Account Risk & Standard Sizer</span>
          </h3>

          <form onSubmit={handleSizerCalc} className="space-y-4">
            <div className="grid grid-cols-2 gap-4 text-xs font-mono">
              <div className="space-y-1.5">
                <label className="text-slate-400 block font-bold">Account Balance (USD)</label>
                <input
                  type="number"
                  value={balance}
                  onChange={(e) => setBalance(Number(e.target.value))}
                  className="w-full bg-[#11111a] border border-white/5 py-2 px-3 text-slate-200 rounded-lg focus:outline-none focus:border-amber-500"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-slate-400 block font-bold">Risk Ratio (%)</label>
                <input
                  type="number"
                  step="0.1"
                  value={riskPercent}
                  onChange={(e) => setRiskPercent(Number(e.target.value))}
                  className="w-full bg-[#11111a] border border-white/5 py-2 px-3 text-slate-200 rounded-lg focus:outline-none focus:border-amber-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 text-xs font-mono">
              <div className="space-y-1.5">
                <label className="text-slate-400 block font-bold">Stop Loss (Pips/Ticks)</label>
                <input
                  type="number"
                  value={stopLoss}
                  onChange={(e) => setStopLoss(Number(e.target.value))}
                  className="w-full bg-[#11111a] border border-white/5 py-2 px-3 text-slate-200 rounded-lg focus:outline-none focus:border-amber-500"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-slate-400 block font-bold">Instrument Class</label>
                <select
                  value={instrument}
                  onChange={(e) => setInstrument(e.target.value)}
                  className="w-full bg-[#11111a] border border-white/5 py-2 px-3 text-slate-300 rounded-lg focus:outline-none focus:border-amber-500"
                >
                  <option value="Forex">Forex Contracts (1 Lot = 100K)</option>
                  <option value="Crypto">Crypto Pairs</option>
                  <option value="Stocks">Equities Class</option>
                  <option value="Indices">Indices Contracts</option>
                </select>
              </div>
            </div>

            <button
              type="submit"
              disabled={sizeLoading}
              className="w-full bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-black py-2.5 rounded-xl font-bold text-xs"
            >
              {sizeLoading ? 'Calculating Sizing...' : 'COMPUTE CONTRACT SIZE'}
            </button>
          </form>

          {/* Sizer Outputs */}
          {sizeRes && (
            <div className="bg-[#10101c]/60 border border-white/5 rounded-xl p-4 divide-y divide-white/5 font-mono text-xs text-slate-300">
              <div className="flex justify-between py-2.5">
                <span className="text-slate-400">Total Capital Sized</span>
                <span className="text-slate-100 font-bold">${sizeRes.accountBalance?.toLocaleString()}</span>
              </div>
              <div className="flex justify-between py-2.5">
                <span className="text-slate-400">Allowed Cash Risk Value</span>
                <span className="text-rose-400 font-extrabold font-bold">${sizeRes.riskAmount?.toFixed(2)}</span>
              </div>
              <div className="flex justify-between py-2.5">
                <span className="text-slate-400">Calculated contract Size</span>
                <div className="text-right">
                  <span className="text-emerald-400 font-black text-sm block">
                    {sizeRes.lotsSized?.toFixed(4)} Lots
                  </span>
                  <span className="text-[10px] text-slate-500 block">({sizeRes.unitsSized?.toLocaleString()} nominal contract units)</span>
                </div>
              </div>
              <div className="flex justify-between py-2.5">
                <span className="text-slate-400">Pip Value representation</span>
                <span className="text-slate-200">${sizeRes.pipValueRepresentation?.toFixed(2)} / Pip</span>
              </div>
            </div>
          )}
        </div>

        {/* Module 2: DCA Multi-Tier Grid Calculator */}
        <div className="bg-[#08080d] border border-white/5 rounded-2xl p-6 space-y-6 shadow-xl">
          <h3 className="text-base font-extrabold text-white uppercase tracking-wider flex items-center space-x-2">
            <TrendingUp className="h-4.5 w-4.5 text-amber-500" />
            <span>Multi-Tier Martingale DCA Grid</span>
          </h3>

          <form onSubmit={handleGridCalc} className="space-y-4">
            <div className="grid grid-cols-2 gap-4 text-xs font-mono">
              <div className="space-y-1.5">
                <label className="text-slate-400 block font-bold">Base Order Size ($)</label>
                <input
                  type="number"
                  value={dcaBase}
                  onChange={(e) => setDcaBase(Number(e.target.value))}
                  className="w-full bg-[#11111a] border border-white/5 py-2 px-3 text-slate-200 rounded-lg focus:outline-none focus:border-amber-500"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-slate-400 block font-bold">Safety Steps Count (5-15)</label>
                <input
                  type="number"
                  min="3"
                  max="15"
                  value={dcaSteps}
                  onChange={(e) => setDcaSteps(Number(e.target.value))}
                  className="w-full bg-[#11111a] border border-white/5 py-2 px-3 text-slate-200 rounded-lg focus:outline-none focus:border-amber-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 text-xs font-mono">
              <div className="space-y-1.5">
                <label className="text-slate-400 block font-bold">Martingale Multiplier</label>
                <input
                  type="number"
                  step="0.05"
                  value={dcaMultiplier}
                  onChange={(e) => setDcaMultiplier(Number(e.target.value))}
                  className="w-full bg-[#11111a] border border-white/5 py-2 px-3 text-slate-200 rounded-lg focus:outline-none focus:border-amber-500"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-slate-400 block font-bold">Step Deviation (%)</label>
                <input
                  type="number"
                  step="0.1"
                  value={dcaDeviation}
                  onChange={(e) => setDcaDeviation(Number(e.target.value))}
                  className="w-full bg-[#11111a] border border-white/5 py-2 px-3 text-slate-200 rounded-lg focus:outline-none focus:border-amber-500"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={gridLoading}
              className="w-full bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-black py-2.5 rounded-xl font-bold text-xs"
            >
              {gridLoading ? 'Simulating Grid Steps...' : 'SIMULATE COMPOUNDING GRID'}
            </button>
          </form>

          {/* DCA Step Grid Outputs */}
          {gridRes && (
            <div className="space-y-4 font-mono text-xs">
              <div className="grid grid-cols-2 gap-4 bg-[#10101c]/60 p-3 rounded-xl border border-white/5">
                <div>
                  <span className="text-slate-500 text-[10px] uppercase block">Cumulative cost</span>
                  <span className="text-amber-500 font-extrabold text-sm block">
                    ${gridRes.summary?.totalInvestmentRequired?.toLocaleString()}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 text-[10px] uppercase block">Weighted Average Entry Deviation</span>
                  <span className="text-slate-200 font-bold text-sm block">
                    -{gridRes.summary?.finalBreakevenDeviationPercent?.toFixed(1)}%
                  </span>
                </div>
              </div>

              <div className="overflow-x-auto rounded-lg border border-white/5 bg-[#0e0e15]">
                <table className="w-full text-left text-[11px]">
                  <thead>
                    <tr className="border-b border-white/5 bg-[#12121e] text-slate-500 font-bold text-[9px] uppercase">
                      <th className="py-2.5 px-3">Step</th>
                      <th className="py-2.5 px-3">Price Dev</th>
                      <th className="py-2.5 px-3">Size ($)</th>
                      <th className="py-2.5 px-3 text-right">Cumulative ($)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5 text-slate-300">
                    {gridRes.gridSteps?.map((stp) => (
                      <tr key={stp.stepNumber}>
                        <td className="py-2 px-3 text-slate-400 font-bold">
                          {stp.stepNumber === 0 ? 'Base' : `SO #${stp.stepNumber}`}
                        </td>
                        <td className="py-2 px-3 text-rose-400">-{stp.deviationPercent?.toFixed(2)}%</td>
                        <td className="py-2 px-3 text-slate-200">${Math.round(stp.orderAmount)}</td>
                        <td className="py-2 px-3 text-right text-amber-500 font-semibold">${Math.round(stp.cumulativeAmount)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

      </div>

    </div>
  );
};
