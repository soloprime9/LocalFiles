/**
 * Centered error boundary middleware for sanitizing response payloads.
 * Includes Mongoose schema validation parser and clean developer stack trace toggles.
 */
export const errorHandler = (err, req, res, next) => {
  let error = { ...err };
  error.message = err.message;

  // Log to console for debugging in dev
  if (process.env.NODE_ENV === 'development') {
    console.error('ErrorHandler Caught:', err);
  }

  // Mongoose Bad ObjectId (Cast Error)
  if (err.name === 'CastError') {
    const message = `Resource not found with format of: ${err.value}`;
    error = new Error(message);
    res.statusCode = 404;
  }

  // Mongoose Duplicate Key Code
  if (err.code === 11000) {
    const message = 'The requested value already exists in our database. Duplicate entries are prevented.';
    error = new Error(message);
    res.statusCode = 400;
  }

  // Mongoose Validation Errors
  if (err.name === 'ValidationError') {
    const message = Object.values(err.errors).map(val => val.message).join(', ');
    error = new Error(message);
    res.statusCode = 400;
  }

  const statusCode = res.statusCode && res.statusCode !== 200 ? res.statusCode : 500;

  res.status(statusCode).json({
    success: false,
    error: error.message || 'Server Error',
    stack: process.env.NODE_ENV === 'production' ? undefined : err.stack
  });
};

export default errorHandler;
