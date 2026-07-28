import React, { useState, useEffect } from 'react';
import { apiService } from '../utils/api';
import { setSeo } from '../utils/seo';
import { Spinner } from '../components/ui/Spinner';
import { Badge } from '../components/ui/Badge';
import { 
  Calendar, 
  Clock, 
  Info, 
  TrendingUp, 
  CheckCircle2, 
  AlertTriangle,
  Flame,
  UserX
} from 'lucide-react';

export const MacroCalendar = () => {
  const [events, setEvents] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setSeo({
  title: `${fetchedInd.name} — Review, Parameters, and Audits | FalconSpido`,
  description: fetchedInd.description || `${fetchedInd.name} reviews, parameters, and trust score on FalconSpido.`,
  path: `/indicators/${fetchedInd.slug}`
});

    const fetchCalendar = async () => {
      setIsLoading(true);
      try {
        const res = await apiService.getMacroCalendar();
        if (res?.success) {
          setEvents(res.data);
        }
      } catch (err) {
        console.error('Failed to prehydrate macro events calendar:', err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchCalendar();
  }, []);

  const getImpactBadge = (imp) => {
    switch (imp) {
      case 'High':
        return <span className="bg-rose-500/10 text-rose-400 border border-rose-500/30 text-[9px] font-black px-2 py-0.5 rounded font-mono uppercase tracking-wider select-none animate-pulse">◆ High Volatility</span>;
      case 'Medium':
        return <span className="bg-amber-500/10 text-amber-400 border border-amber-500/30 text-[9px] font-bold px-2 py-0.5 rounded font-mono uppercase tracking-wider select-none">◆ Medium Volatility</span>;
      default:
        return <span className="bg-slate-500/10 text-slate-400 border border-slate-500/30 text-[9px] px-2 py-0.5 rounded font-mono uppercase select-none">◇ Low</span>;
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      
      {/* Title */}
      <div className="space-y-1">
        <span className="text-[10px] text-rose-400 uppercase tracking-widest font-extrabold flex items-center space-x-1">
          <Calendar className="h-4.5 w-4.5 text-rose-500" />
          <span>Macroeconomic Volatility Index</span>
        </span>
        <h1 className="text-xl sm:text-3xl font-black text-white">Scheduled Volatility Events Calendar</h1>
        <p className="text-xs text-slate-400 max-w-xl">
          Scheduled macroeconomic events, central bank releases, and inflation indexes. Automated traders should review high-impact guidelines to safely pause automated bots before high-volatility spikes.
        </p>
      </div>

      {isLoading && events.length === 0 ? (
        <div className="py-20 flex flex-col items-center">
          <Spinner size="lg" />
          <p className="text-xs text-slate-500 font-mono">Synchronizing central bank releases calendars...</p>
        </div>
      ) : (
        <div className="bg-[#08080d] border border-[#171724] rounded-2xl overflow-hidden shadow-2xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300 font-mono border-collapse">
              <thead>
                <tr className="border-b border-white/5 bg-[#0c0c14] text-[#94a3b8] text-[9px] uppercase tracking-wider select-none">
                  <th className="py-3 px-5 font-bold">Country / Currency</th>
                  <th className="py-3 px-5 font-bold">Release Scheduled Event</th>
                  <th className="py-3 px-5 font-bold">Volatility Scale</th>
                  <th className="py-3 px-5 font-bold text-center">Previous Stats</th>
                  <th className="py-3 px-5 font-bold text-center">Forecast parameters</th>
                  <th className="py-3 px-5 font-bold text-center">Actual Change</th>
                  <th className="py-3 px-5 font-bold text-right">Bot action Guide</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 leading-relaxed text-[11px]">
                {events.map((evt) => (
                  <tr key={evt._id} className="hover:bg-white/5 transition-colors">
                    
                    <td className="py-4.5 px-5 font-bold text-white">
                      <div className="flex items-center space-x-2">
                        <span className="text-sm">{evt.country}</span>
                        <Badge variant="blue">{evt.currencyAffected}</Badge>
                      </div>
                    </td>

                    <td className="py-4.5 px-5 font-semibold text-slate-200">
                      <div className="space-y-0.5">
                        <span className="block text-[12px]">{evt.title}</span>
                        <span className="text-[9px] text-[#818cf8] uppercase tracking-wide font-mono block">
                          Scheduled: {evt.eventTime}
                        </span>
                      </div>
                    </td>

                    <td className="py-4.5 px-5">{getImpactBadge(evt.impact)}</td>

                    <td className="py-4.5 px-5 text-center text-slate-400">
                      {evt.previousValue || '--'}
                    </td>

                    <td className="py-4.5 px-5 text-center text-[#e2e8f0] font-bold">
                      {evt.forecastValue || '--'}
                    </td>

                    <td className="py-4.5 px-5 text-center font-extrabold text-amber-400">
                      {evt.actualValue || 'Pending'}
                    </td>

                    <td className="py-4.5 px-5 text-right font-semibold">
                      <span className={`px-2.5 py-1 rounded text-[10px] font-bold ${
                        evt.impact === 'High' ? 'bg-rose-500/10 text-rose-400 animate-pulse border border-rose-500/20' : 'bg-emerald-500/10 text-emerald-400'
                      }`}>
                        {evt.recommendedAction || 'Monitor parameters'}
                      </span>
                    </td>

                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Volatility caution banner */}
      <div className="bg-rose-500/5 border border-rose-500/10 p-5 rounded-2xl flex items-start space-x-3 text-xs text-rose-300">
        <AlertTriangle className="h-5 w-5 text-rose-400 flex-shrink-0 mt-0.5" />
        <div className="space-y-1">
          <span className="font-extrabold text-white block">CRITICAL EA EXECUTION PRE-ALERT:</span>
          <p className="leading-relaxed">
            Forex grid EAs and automated scalpers are extremely susceptible to dynamic distribution expansion (spread expansion) and margin call sweeps during high-impact news spikes (denoted above as ◆ High Volatility). We strongly advise setting up automated news-filters inside indicator scripts, or manually placing bots in paused stand-by states at least 15 minutes before and after listed schedules.
          </p>
        </div>
      </div>

    </div>
  );
};
