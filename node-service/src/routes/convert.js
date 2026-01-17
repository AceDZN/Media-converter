/**
 * Conversion API routes
 */
const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs').promises;
const { v4: uuidv4 } = require('uuid');
const config = require('../config');
const { convertPptxToImages, convertPdfToImagesJob } = require('../services/converter');

const router = express.Router();

// Configure multer for file uploads
const storage = multer.diskStorage({
  destination: async (req, file, cb) => {
    const jobId = uuidv4();
    req.jobId = jobId;
    const uploadDir = path.join(config.uploadDir, 'temp', jobId);
    await fs.mkdir(uploadDir, { recursive: true });
    cb(null, uploadDir);
  },
  filename: (req, file, cb) => {
    const ext = path.extname(file.originalname).toLowerCase();
    cb(null, `input${ext}`);
  },
});

const upload = multer({
  storage,
  limits: {
    fileSize: config.maxFileSizeMb * 1024 * 1024,
  },
  fileFilter: (req, file, cb) => {
    const ext = path.extname(file.originalname).toLowerCase();
    const allowedExts = [...config.allowedPptxExtensions, ...config.allowedPdfExtensions];
    if (allowedExts.includes(ext)) {
      cb(null, true);
    } else {
      cb(new Error(`Invalid file type '${ext}'. Allowed: ${allowedExts.join(', ')}`));
    }
  },
});

/**
 * POST /pptx-to-image
 * Convert PPTX/PPT to images
 */
router.post('/pptx-to-image', upload.single('file'), async (req, res) => {
  const startTime = Date.now();

  if (!req.file) {
    return res.status(400).json({ error: 'ValidationError', detail: 'No file uploaded' });
  }

  const ext = path.extname(req.file.originalname).toLowerCase();
  if (!config.allowedPptxExtensions.includes(ext)) {
    return res.status(400).json({
      error: 'ValidationError',
      detail: `Invalid file type '${ext}'. Allowed: ${config.allowedPptxExtensions.join(', ')}`,
    });
  }

  const jobId = req.jobId;
  console.log(`Received file: ${req.file.originalname} (${req.file.size} bytes) -> Job ${jobId}`);

  try {
    const result = await convertPptxToImages(req.file.path, jobId);

    if (!result.success) {
      return res.status(500).json({
        error: 'ConversionError',
        detail: result.error,
        job_id: jobId,
      });
    }

    res.json({
      job_id: jobId,
      status: 'completed',
      message: `Successfully converted ${result.slideCount} slides`,
      total_slides: result.slideCount,
      images: result.images,
      processing_time_ms: result.processingTimeMs,
    });
  } catch (error) {
    console.error(`Job ${jobId} failed:`, error);
    res.status(500).json({
      error: 'ConversionError',
      detail: error.message,
      job_id: jobId,
    });
  }
});

/**
 * POST /pdf-to-image
 * Convert PDF to images
 */
router.post('/pdf-to-image', upload.single('file'), async (req, res) => {
  if (!req.file) {
    return res.status(400).json({ error: 'ValidationError', detail: 'No file uploaded' });
  }

  const ext = path.extname(req.file.originalname).toLowerCase();
  if (!config.allowedPdfExtensions.includes(ext)) {
    return res.status(400).json({
      error: 'ValidationError',
      detail: `Invalid file type '${ext}'. Allowed: ${config.allowedPdfExtensions.join(', ')}`,
    });
  }

  const jobId = req.jobId;
  console.log(`Received PDF file: ${req.file.originalname} (${req.file.size} bytes) -> Job ${jobId}`);

  try {
    const result = await convertPdfToImagesJob(req.file.path, jobId);

    if (!result.success) {
      return res.status(500).json({
        error: 'ConversionError',
        detail: result.error,
        job_id: jobId,
      });
    }

    res.json({
      job_id: jobId,
      status: 'completed',
      message: `Successfully converted ${result.slideCount} pages`,
      total_slides: result.slideCount,
      images: result.images,
      processing_time_ms: result.processingTimeMs,
    });
  } catch (error) {
    console.error(`Job ${jobId} failed:`, error);
    res.status(500).json({
      error: 'ConversionError',
      detail: error.message,
      job_id: jobId,
    });
  }
});

// Error handling middleware for multer errors
router.use((error, req, res, next) => {
  if (error instanceof multer.MulterError) {
    if (error.code === 'LIMIT_FILE_SIZE') {
      return res.status(413).json({
        error: 'FileTooLarge',
        detail: `File too large. Maximum size: ${config.maxFileSizeMb}MB`,
      });
    }
    return res.status(400).json({
      error: 'UploadError',
      detail: error.message,
    });
  }
  if (error) {
    return res.status(400).json({
      error: 'ValidationError',
      detail: error.message,
    });
  }
  next();
});

module.exports = router;
