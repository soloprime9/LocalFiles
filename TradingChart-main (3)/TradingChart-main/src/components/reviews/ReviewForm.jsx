'use client'
import { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import toast from 'react-hot-toast';
import StarRating from '../ui/StarRating';
import { createReview } from '../../utils/api';

const REVIEWER_TYPES = ['Beginner', 'Intermediate', 'Pro', 'Institutional'];
const MIN_BODY_LENGTH = 50;

const initialForm = {
  reviewerName: '',
  reviewerType: 'Beginner',
  rating: 0,
  title: '',
  body: '',
  tradingPeriod: '',
  assetTraded: '',
  timeframeUsed: '',
  platform: '',
  profitableForReviewer: true,
  wouldRecommend: true,
};

export default function ReviewForm({ indicatorId, onSuccess = () => {} }) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(initialForm);
  const [submitting, setSubmitting] = useState(false);

  const update = (key, value) => setForm((f) => ({ ...f, [key]: value }));

  const isValid =
    form.reviewerName.trim() &&
    form.rating > 0 &&
    form.title.trim() &&
    form.body.trim().length >= MIN_BODY_LENGTH;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!isValid) {
      toast.error('Please fill all required fields. Review must be at least 50 characters.');
      return;
    }
    setSubmitting(true);
    try {
      await createReview(indicatorId, form);
      toast.success('Review submitted. Thank you!');
      setForm(initialForm);
      setOpen(false);
      onSuccess();
    } catch {
      toast.error('Could not submit review. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="bg-[#111111] border border-[#1F2937] rounded-xl">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between p-5"
      >
        <span className="text-white font-semibold">Write a Review</span>
        <ChevronDown className={`w-5 h-5 text-gray-500 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <form onSubmit={handleSubmit} className="px-5 pb-5 space-y-4">
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1.5">Your Name *</label>
              <input
                type="text"
                value={form.reviewerName}
                onChange={(e) => update('reviewerName', e.target.value)}
                className="w-full bg-[#0A0A0A] border border-[#1F2937] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-amber-500/50"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1.5">Experience Level</label>
              <select
                value={form.reviewerType}
                onChange={(e) => update('reviewerType', e.target.value)}
                className="w-full bg-[#0A0A0A] border border-[#1F2937] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-amber-500/50"
              >
                {REVIEWER_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1.5">Rating *</label>
            <StarRating rating={form.rating} interactive onChange={(n) => update('rating', n)} size="lg" />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1.5">Review Title *</label>
            <input
              type="text"
              value={form.title}
              onChange={(e) => update('title', e.target.value)}
              className="w-full bg-[#0A0A0A] border border-[#1F2937] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-amber-500/50"
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1.5">
              Your Experience * <span className="text-gray-600">(min {MIN_BODY_LENGTH} characters)</span>
            </label>
            <textarea
              value={form.body}
              onChange={(e) => update('body', e.target.value)}
              rows={4}
              className="w-full bg-[#0A0A0A] border border-[#1F2937] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-amber-500/50 resize-none"
            />
            <span
              className={`text-xs ${form.body.length >= MIN_BODY_LENGTH ? 'text-emerald-400' : 'text-gray-500'}`}
            >
              {form.body.length} / {MIN_BODY_LENGTH}
            </span>
          </div>

          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1.5">Trading Period</label>
              <input
                type="text"
                placeholder="e.g. 30 days"
                value={form.tradingPeriod}
                onChange={(e) => update('tradingPeriod', e.target.value)}
                className="w-full bg-[#0A0A0A] border border-[#1F2937] rounded-lg px-3 py-2 text-sm text-white placeholder:text-gray-600 focus:outline-none focus:ring-2 focus:ring-amber-500/50"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1.5">Asset Traded</label>
              <input
                type="text"
                placeholder="e.g. EUR/USD"
                value={form.assetTraded}
                onChange={(e) => update('assetTraded', e.target.value)}
                className="w-full bg-[#0A0A0A] border border-[#1F2937] rounded-lg px-3 py-2 text-sm text-white placeholder:text-gray-600 focus:outline-none focus:ring-2 focus:ring-amber-500/50"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1.5">Timeframe Used</label>
              <input
                type="text"
                placeholder="e.g. H4"
                value={form.timeframeUsed}
                onChange={(e) => update('timeframeUsed', e.target.value)}
                className="w-full bg-[#0A0A0A] border border-[#1F2937] rounded-lg px-3 py-2 text-sm text-white placeholder:text-gray-600 focus:outline-none focus:ring-2 focus:ring-amber-500/50"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1.5">Platform Used</label>
              <input
                type="text"
                placeholder="e.g. MT5"
                value={form.platform}
                onChange={(e) => update('platform', e.target.value)}
                className="w-full bg-[#0A0A0A] border border-[#1F2937] rounded-lg px-3 py-2 text-sm text-white placeholder:text-gray-600 focus:outline-none focus:ring-2 focus:ring-amber-500/50"
              />
            </div>
          </div>

          <div className="flex flex-wrap gap-6">
            <div>
              <span className="block text-sm text-gray-400 mb-2">Was it profitable for you?</span>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => update('profitableForReviewer', true)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                    form.profitableForReviewer
                      ? 'bg-emerald-500 text-black border-emerald-500'
                      : 'border-[#1F2937] text-gray-300'
                  }`}
                >
                  Yes
                </button>
                <button
                  type="button"
                  onClick={() => update('profitableForReviewer', false)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                    !form.profitableForReviewer
                      ? 'bg-red-500 text-black border-red-500'
                      : 'border-[#1F2937] text-gray-300'
                  }`}
                >
                  No
                </button>
              </div>
            </div>
            <div>
              <span className="block text-sm text-gray-400 mb-2">Would you recommend it?</span>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => update('wouldRecommend', true)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                    form.wouldRecommend
                      ? 'bg-emerald-500 text-black border-emerald-500'
                      : 'border-[#1F2937] text-gray-300'
                  }`}
                >
                  Yes
                </button>
                <button
                  type="button"
                  onClick={() => update('wouldRecommend', false)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                    !form.wouldRecommend
                      ? 'bg-red-500 text-black border-red-500'
                      : 'border-[#1F2937] text-gray-300'
                  }`}
                >
                  No
                </button>
              </div>
            </div>
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full bg-amber-500 text-black font-semibold rounded-lg py-2.5 hover:bg-amber-400 disabled:opacity-50 transition-colors"
          >
            {submitting ? 'Submitting…' : 'Submit Review'}
          </button>
        </form>
      )}
    </div>
  );
}
