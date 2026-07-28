'use client'
import React, { useState } from 'react';
import { submitListing } from '../utils/api';
import toast from 'react-hot-toast';
import { PlusCircleIcon, CheckCircleIcon } from '@heroicons/react/24/outline';

const LISTING_TYPES = ['indicator', 'ea', 'bot', 'signal', 'strategy', 'script', 'tool'];
const PLATFORMS = ['TradingView', 'MetaTrader4', 'MetaTrader5', 'cTrader', 'NinjaTrader', 'ThinkOrSwim', 'Other'];
const PRICING_MODELS = ['free', 'one-time', 'subscription', 'freemium'];

export default function SubmitListing() {
  const [form, setForm] = useState({
    name: '',
    shortDescription: '',
    description: '',
    author: '',
    listingType: 'indicator',
    platforms: [],
    pricingModel: 'free',
    price: '',
    externalUrl: '',
    category: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  const set = (key, val) => setForm((f) => ({ ...f, [key]: val }));

  const togglePlatform = (p) => {
    set('platforms', form.platforms.includes(p)
      ? form.platforms.filter((x) => x !== p)
      : [...form.platforms, p]
    );
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.name || !form.shortDescription || !form.externalUrl) {
      toast.error('Please fill in all required fields');
      return;
    }
    setSubmitting(true);
    try {
      await submitListing(form);
      setDone(true);
    } finally {
      setSubmitting(false);
    }
  };

  if (done) {
    return (
      <div className="max-w-xl mx-auto px-4 py-20 text-center">
        <CheckCircleIcon className="w-16 h-16 text-green-400 mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-white mb-3">Listing Submitted!</h2>
        <p className="text-gray-400 text-sm mb-6">
          Thank you! Your listing is under review and will be published once approved.
        </p>
        <button onClick={() => setDone(false)} className="btn-secondary">
          Submit Another
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-10">
      <div className="flex items-center gap-3 mb-8">
        <div className="w-10 h-10 rounded-lg bg-amber-500/10 flex items-center justify-center">
          <PlusCircleIcon className="w-5 h-5 text-amber-400" />
        </div>
        <div>
          <h1 className="section-title">Submit a Listing</h1>
          <p className="section-subtitle">Share your indicator, EA, bot, or signal service</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Name */}
        <div>
          <label className="block text-sm text-gray-400 mb-1.5">
            Tool Name <span className="text-red-400">*</span>
          </label>
          <input
            type="text"
            value={form.name}
            onChange={(e) => set('name', e.target.value)}
            placeholder="e.g. SuperTrend Pro"
            className="input-field"
          />
        </div>

        {/* Type */}
        <div>
          <label className="block text-sm text-gray-400 mb-1.5">Listing Type</label>
          <div className="flex flex-wrap gap-2">
            {LISTING_TYPES.map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => set('listingType', t)}
                className={`px-3 py-1.5 rounded-md text-xs font-medium border transition-colors capitalize ${
                  form.listingType === t
                    ? 'border-amber-500 bg-amber-500/10 text-amber-400'
                    : 'border-[#1F2937] text-gray-500 hover:border-[#374151] hover:text-gray-300'
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        {/* Platforms */}
        <div>
          <label className="block text-sm text-gray-400 mb-1.5">Platforms</label>
          <div className="flex flex-wrap gap-2">
            {PLATFORMS.map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => togglePlatform(p)}
                className={`px-3 py-1.5 rounded-md text-xs font-medium border transition-colors ${
                  form.platforms.includes(p)
                    ? 'border-blue-500 bg-blue-500/10 text-blue-400'
                    : 'border-[#1F2937] text-gray-500 hover:border-[#374151] hover:text-gray-300'
                }`}
              >
                {p}
              </button>
            ))}
          </div>
        </div>

        {/* Author */}
        <div>
          <label className="block text-sm text-gray-400 mb-1.5">Author / Creator</label>
          <input
            type="text"
            value={form.author}
            onChange={(e) => set('author', e.target.value)}
            placeholder="Your name or brand"
            className="input-field"
          />
        </div>

        {/* Short Description */}
        <div>
          <label className="block text-sm text-gray-400 mb-1.5">
            Short Description <span className="text-red-400">*</span>
          </label>
          <input
            type="text"
            value={form.shortDescription}
            onChange={(e) => set('shortDescription', e.target.value)}
            placeholder="One-line summary (shown in cards)"
            className="input-field"
            maxLength={150}
          />
          <p className="text-gray-700 text-xs mt-1">{form.shortDescription.length}/150</p>
        </div>

        {/* Full Description */}
        <div>
          <label className="block text-sm text-gray-400 mb-1.5">Full Description</label>
          <textarea
            rows={5}
            value={form.description}
            onChange={(e) => set('description', e.target.value)}
            placeholder="Detailed description, features, how it works..."
            className="input-field resize-none"
          />
        </div>

        {/* Pricing */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1.5">Pricing Model</label>
            <select
              value={form.pricingModel}
              onChange={(e) => set('pricingModel', e.target.value)}
              className="input-field"
            >
              {PRICING_MODELS.map((m) => (
                <option key={m} value={m} className="capitalize">{m}</option>
              ))}
            </select>
          </div>
          {form.pricingModel !== 'free' && (
            <div>
              <label className="block text-sm text-gray-400 mb-1.5">Price (USD)</label>
              <input
                type="number"
                value={form.price}
                onChange={(e) => set('price', e.target.value)}
                placeholder="0.00"
                min="0"
                className="input-field"
              />
            </div>
          )}
        </div>

        {/* External URL */}
        <div>
          <label className="block text-sm text-gray-400 mb-1.5">
            URL / Link <span className="text-red-400">*</span>
          </label>
          <input
            type="url"
            value={form.externalUrl}
            onChange={(e) => set('externalUrl', e.target.value)}
            placeholder="https://..."
            className="input-field"
          />
        </div>

        <div className="pt-2">
          <button type="submit" disabled={submitting} className="btn-primary w-full py-3 text-base">
            {submitting ? 'Submitting...' : 'Submit for Review'}
          </button>
          <p className="text-gray-600 text-xs text-center mt-2">
            Listings are manually reviewed before publishing.
          </p>
        </div>
      </form>
    </div>
  );
}
