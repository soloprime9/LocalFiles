import cron from 'node-cron';
import { Indicator } from '../models/index.js';

/**
 * Scheduled job to reset temporary weekly counters.
 * Triggers every Sunday at 00:00 (Midnight).
 */
export const startResetWeeklyStatsJob = () => {
  cron.schedule('0 0 * * 0', async () => {
    console.info('🕒 [Cron Job] Starting weekly stats reset task...');
    
    try {
      const indicators = await Indicator.find({ status: 'active' });
      let updatedCount = 0;

      for (const ind of indicators) {
        // Cache original values for logging or safety checks if needed
        ind.weeklyViews = 0;
        ind.weeklyLikes = 0;
        
        // Re-saving triggers pre('save') calculation of trendingScore and TrustScore
        await ind.save();
        updatedCount++;
      }

      console.log(`✓ [Cron Job] Weekly stats reset completed. Recalculated ${updatedCount} tools.`);
    } catch (err) {
      console.error('✗ [Cron Job] Error running weekly stats reset task:', err.message);
    }
  });

  console.log('✓ [Cron Job] Weekly stats reset scheduler loaded successfully.');
};

export default startResetWeeklyStatsJob;
