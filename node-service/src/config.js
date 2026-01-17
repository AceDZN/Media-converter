/**
 * Application configuration
 */
const config = {
  port: parseInt(process.env.PORT || '8000', 10),
  uploadDir: process.env.UPLOAD_DIR || './uploads',
  maxFileSizeMb: parseInt(process.env.MAX_FILE_SIZE_MB || '100', 10),
  imageDpi: parseInt(process.env.IMAGE_DPI || '200', 10),
  imageFormat: process.env.IMAGE_FORMAT || 'jpeg',
  jpegQuality: parseInt(process.env.JPEG_QUALITY || '90', 10),
  jobTimeoutSeconds: parseInt(process.env.JOB_TIMEOUT_SECONDS || '300', 10),
  allowedPptxExtensions: ['.ppt', '.pptx'],
  allowedPdfExtensions: ['.pdf'],
};

module.exports = config;
