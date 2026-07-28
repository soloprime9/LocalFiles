import { ShieldCheck, ShieldAlert, ShieldQuestion, Radio } from 'lucide-react';

const AUDIT_CONFIG = {
  Verified: { icon: ShieldCheck, classes: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30' },
  Suspicious: { icon: ShieldAlert, classes: 'bg-red-500/15 text-red-400 border-red-500/30' },
  Unaudited: { icon: ShieldQuestion, classes: 'bg-gray-500/15 text-gray-400 border-gray-500/30' },
};

function StatBlock({ label, value, colorClass = 'text-white' }) {
  return (
    <div className="bg-[#0A0A0A] border border-[#1F2937] rounded-lg p-3">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className={`text-lg font-semibold ${colorClass}`}>{value}</p>
    </div>
  );
}

export default function BacktestCard({ backtestData }) {
  if (!backtestData) return null;

  const {
    winRate,
    sharpeRatio,
    sortinoRatio,
    maxDrawdown,
    profitFactor,
    totalTrades,
    avgTradesPerMonth,
    backtestPeriod,
    backtestCapital,
    auditStatus = 'Unaudited',
    forwardTestActive,
  } = backtestData;

  const audit = AUDIT_CONFIG[auditStatus] || AUDIT_CONFIG.Unaudited;
  const AuditIcon = audit.icon;

  return (
    <div className="bg-[#111111] border border-[#1F2937] rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-white font-semibold">Backtest Results</h3>
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium border ${audit.classes}`}
        >
          <AuditIcon className="w-3.5 h-3.5" />
          {auditStatus}
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-4">
        <StatBlock
          label="Win Rate"
          value={typeof winRate === 'number' ? `${winRate}%` : '—'}
          colorClass={winRate > 60 ? 'text-emerald-400' : 'text-white'}
        />
        <StatBlock
          label="Sharpe Ratio"
          value={sharpeRatio ?? '—'}
          colorClass={sharpeRatio > 1 ? 'text-emerald-400' : 'text-white'}
        />
        <StatBlock label="Sortino Ratio" value={sortinoRatio ?? '—'} />
        <StatBlock
          label="Max Drawdown"
          value={typeof maxDrawdown === 'number' ? `${maxDrawdown}%` : '—'}
          colorClass="text-red-400"
        />
        <StatBlock label="Profit Factor" value={profitFactor ?? '—'} />
        <StatBlock label="Total Trades" value={totalTrades ?? '—'} />
        <StatBlock label="Avg Trades / Month" value={avgTradesPerMonth ?? '—'} />
        <StatBlock label="Backtest Period" value={backtestPeriod || '—'} />
        <StatBlock
          label="Starting Capital"
          value={backtestCapital ? `$${backtestCapital.toLocaleString()}` : '—'}
        />
      </div>

      {auditStatus === 'Suspicious' && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-sm text-red-300 flex items-start gap-2">
          <span aria-hidden>⚠️</span>
          <span>This backtest may be curve-fitted. Red flags detected. Trade with extreme caution.</span>
        </div>
      )}

      {auditStatus === 'Verified' && (
        <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-3 text-sm text-emerald-300 flex items-start gap-2">
          <span aria-hidden>✓</span>
          <span>This backtest has been manually audited by the IndicatorHub team.</span>
        </div>
      )}

      {forwardTestActive && (
        <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3 text-sm text-blue-300 flex items-start gap-2 mt-3">
          <Radio className="w-4 h-4 shrink-0 mt-0.5" />
          <span>Live forward-test in progress.</span>
        </div>
      )}
    </div>
  );
}
