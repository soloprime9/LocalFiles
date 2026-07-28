/**
 * Lightweight middleware schema validator.
 * Validates request bodies against an expected list of parameters.
 */
export const validateFields = (requiredFields) => {
  return (req, res, next) => {
    const missing = [];
    requiredFields.forEach(field => {
      if (req.body[field] === undefined || req.body[field] === null || req.body[field] === '') {
        missing.push(field);
      }
    });

    if (missing.length > 0) {
      return res.status(400).json({
        success: false,
        error: `Required input values are missing or blank: ${missing.join(', ')}`
      });
    }

    next();
  };
};

export default validateFields;
