import mongoose from 'mongoose';

/**
 * Establishment of database communication.
 * Handles production-grade failover and exponential retry metrics.
 */
import dns from 'node:dns/promises';
dns.setServers(["1.1.1.1", "8.8.8.8"]);

console.log("Mera Mongo URL yeh hai:", process.env.MONGO_URI);

export const connectDB = async () => {

  const uri = process.env.MONGO_URI 
  const maxRetries = 1;
  let retryCount = 0;

  mongoose.connection.on('connected', () => {
    console.info(`✓ MongoDB Connection established successfully.`);
  });

  mongoose.connection.on('error', (err) => {
    console.error(`✗ MongoDB Connection Error:`, err);
  });

  mongoose.connection.on('disconnected', () => {
    console.warn(`! MongoDB Connection severed. Retrying...`);
  });

  while (retryCount < maxRetries) {
    try {
      const conn = await mongoose.connect(uri, {
        serverSelectionTimeoutMS: 5000,
        socketTimeoutMS: 45000,
      });
      console.log(`✓ MongoDB Connected: ${conn.connection.host}`);
      return conn;
    } catch (err) {
      retryCount++;
      console.error(`✗ Connection failure (Attempt ${retryCount}/${maxRetries}): ${err.message}`);
      if (retryCount >= maxRetries) {
        if (process.env.NODE_ENV === 'production') {
          console.error('FATAL: Unable to connect to MongoDB in production state. Shutting down...');
          process.exit(1);
        } else {
          console.warn('Warning: Proceeding with un-established DB connection (development environment fallback).');
          break;
        }
      }
      // Delay exponentially before next attempt
      await new Promise(res => setTimeout(res, Math.pow(2, retryCount) * 1000));
    }
  }
};

export default connectDB;
