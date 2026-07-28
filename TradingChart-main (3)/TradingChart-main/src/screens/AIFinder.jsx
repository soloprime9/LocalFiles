'use client'
import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { CpuChipIcon, ArrowRightIcon, ArrowLeftIcon, CheckIcon } from '@heroicons/react/24/outline';
import { useAppContext, value } from '../context/AppContext';
import { useNavigate } from 'react-router-dom';

const STEPS = [
  {
    id: 'platform',
    question: 'Which platform do you trade on?',
    options: ['TradingView', 'MetaTrader 4', 'MetaTrader 5', 'cTrader', 'NinjaTrader', "Don't know"],
  },
  {
    id: 'asset',
    question: 'What asset class do you trade?',
    options: ['Forex', 'Crypto', 'Stocks', 'Indices', 'Commodities', 'Futures'],
  },
  {
    id: 'strategy',
    question: "What's your trading style?",
    options: ['Scalping', 'Day Trading', 'Swing Trading', 'Position Trading', 'Algorithmic', 'Any'],
  },
  {
    id: 'type',
    question: 'What type of tool are you looking for?',
    options: ['Indicator', 'Expert Advisor (EA)', 'Signal Service', 'Trading Bot', 'Complete Strategy', 'Any'],
  },
  {
    id: 'budget',
    question: "What's your budget?",
    options: ['Free only', 'Under $50', '$50 - $200', '$200+', "Don't mind"],
  },
];

export default function AIFinder() {
  const { dispatch } = useApp();
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState({});

  const current = STEPS[step];
  const isLast = step === STEPS.length - 1;

  const select = (value) => {
    const newAnswers = { ...answers, [current.id]: value };
    setAnswers(newAnswers);

    if (isLast) {
      // Build filters and navigate
      const filterMap = {
        platform: newAnswers.platform !== "Don't know" ? newAnswers.platform?.toLowerCase().replace(' ', '') : '',
        assetClass: newAnswers.asset !== 'Any' ? [newAnswers.asset?.toLowerCase()] : [],
        strategyType: newAnswers.strategy !== 'Any' ? [newAnswers.strategy?.toLowerCase().replace(' ', '-')] : [],
        listingType: newAnswers.type !== 'Any' ? newAnswers.type?.toLowerCase().split(' ')[0] : '',
        isFree: newAnswers.budget === 'Free only',
      };
      dispatch({ type: ACTIONS.SET_FILTER, payload: filterMap });
      navigate('/indicators');
    } else {
      setStep((s) => s + 1);
    }
  };

  const progress = ((step + 1) / STEPS.length) * 100;

  return (
    <div className="min-h-screen bg-[#0A0A0A] flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-[#1F2937]">
        <Link to="/" className="flex items-center gap-2">
          <div className="w-7 h-7 rounded bg-amber-500 flex items-center justify-center">
            <CpuChipIcon className="w-4 h-4 text-black" />
          </div>
          <span className="text-white font-semibold text-sm">
            Indicator<span className="text-amber-400">Hub</span> AI Finder
          </span>
        </Link>
        <Link to="/indicators" className="text-gray-500 hover:text-white text-sm transition-colors">
          Skip → Browse all
        </Link>
      </div>

      {/* Progress */}
      <div className="px-6 pt-4">
        <div className="max-w-xl mx-auto">
          <div className="flex items-center justify-between text-xs text-gray-600 mb-2">
            <span>Step {step + 1} of {STEPS.length}</span>
            <span>{Math.round(progress)}%</span>
          </div>
          <div className="h-1 bg-[#1F2937] rounded-full">
            <div
              className="h-1 bg-amber-500 rounded-full transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </div>

      {/* Question */}
      <div className="flex-1 flex items-center justify-center px-6 py-10">
        <div className="max-w-xl w-full">
          <div className="text-center mb-10">
            <div className="inline-flex items-center gap-2 bg-amber-500/10 border border-amber-500/20 rounded-full px-3 py-1 text-amber-400 text-xs mb-4">
              <CpuChipIcon className="w-3.5 h-3.5" />
              AI-Powered Matching
            </div>
            <h2 className="text-3xl font-bold text-white">{current.question}</h2>
          </div>

          <div className="grid grid-cols-2 gap-3">
            {current.options.map((opt) => {
              const selected = answers[current.id] === opt;
              return (
                <button
                  key={opt}
                  onClick={() => select(opt)}
                  className={`card card-hover p-4 text-left flex items-center justify-between transition-all duration-150 ${
                    selected
                      ? 'border-amber-500 bg-amber-500/10 text-amber-400'
                      : 'text-gray-300 hover:text-white'
                  }`}
                >
                  <span className="text-sm font-medium">{opt}</span>
                  {selected ? (
                    <CheckIcon className="w-4 h-4 text-amber-400" />
                  ) : (
                    <ArrowRightIcon className="w-4 h-4 text-gray-700" />
                  )}
                </button>
              );
            })}
          </div>

          {/* Back */}
          {step > 0 && (
            <div className="text-center mt-6">
              <button
                onClick={() => setStep((s) => s - 1)}
                className="flex items-center gap-2 text-gray-500 hover:text-white text-sm mx-auto transition-colors"
              >
                <ArrowLeftIcon className="w-4 h-4" />
                Back
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
