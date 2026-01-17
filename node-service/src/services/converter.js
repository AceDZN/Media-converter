/**
 * Converter service for PPTX/PDF to Image conversion
 */
const { exec } = require('child_process');
const { promisify } = require('util');
const path = require('path');
const fs = require('fs').promises;
const config = require('../config');

const execAsync = promisify(exec);

/**
 * Convert PPTX/PPT to PDF using LibreOffice
 */
async function convertToPdf(inputPath, outputDir) {
  const cmd = [
    'soffice',
    '--headless',
    '--invisible',
    '--nologo',
    '--nofirststartwizard',
    '--convert-to',
    'pdf',
    '--outdir',
    `"${outputDir}"`,
    `"${inputPath}"`,
  ].join(' ');

  try {
    const { stdout, stderr } = await execAsync(cmd, {
      timeout: config.jobTimeoutSeconds * 1000,
      cwd: outputDir,
    });

    // LibreOffice creates PDF with same base name
    const baseName = path.basename(inputPath, path.extname(inputPath));
    const pdfPath = path.join(outputDir, `${baseName}.pdf`);

    // Check if PDF was created
    try {
      await fs.access(pdfPath);
    } catch {
      throw new Error(`PDF not created. LibreOffice output: ${stdout} ${stderr}`);
    }

    return pdfPath;
  } catch (error) {
    if (error.killed) {
      throw new Error(`LibreOffice conversion timed out after ${config.jobTimeoutSeconds}s`);
    }
    throw new Error(`LibreOffice conversion failed: ${error.message}`);
  }
}

/**
 * Convert PDF to images using pdftoppm (Poppler)
 */
async function convertPdfToImages(pdfPath, outputDir, prefix = 'slide') {
  const format = config.imageFormat === 'png' ? 'png' : 'jpeg';
  const formatFlag = format === 'png' ? '-png' : '-jpeg';

  const outputPrefix = path.join(outputDir, prefix);

  const cmd = [
    'pdftoppm',
    formatFlag,
    `-r ${config.imageDpi}`,
    format === 'jpeg' ? `-jpegopt quality=${config.jpegQuality}` : '',
    `"${pdfPath}"`,
    `"${outputPrefix}"`,
  ].filter(Boolean).join(' ');

  try {
    await execAsync(cmd, {
      timeout: config.jobTimeoutSeconds * 1000,
      cwd: outputDir,
    });

    // Get list of generated images
    const files = await fs.readdir(outputDir);
    const ext = format === 'png' ? 'png' : 'jpg';
    const imageFiles = files
      .filter(f => f.startsWith(prefix) && f.endsWith(`.${ext}`))
      .sort();

    // Rename files to have consistent naming (slide_001.jpg, slide_002.jpg, etc.)
    const imagePaths = [];
    for (let i = 0; i < imageFiles.length; i++) {
      const oldPath = path.join(outputDir, imageFiles[i]);
      const newName = `${prefix}_${String(i + 1).padStart(3, '0')}.${ext}`;
      const newPath = path.join(outputDir, newName);

      // Rename if different
      if (imageFiles[i] !== newName) {
        await fs.rename(oldPath, newPath);
      }

      // Return relative URL path
      const relativePath = path.relative(config.uploadDir, newPath);
      imagePaths.push(`/uploads/${relativePath}`);
    }

    return imagePaths;
  } catch (error) {
    throw new Error(`PDF to image conversion failed: ${error.message}`);
  }
}

/**
 * Convert PPTX to images
 * Pipeline: PPTX -> PDF (LibreOffice) -> Images (Poppler)
 */
async function convertPptxToImages(inputPath, jobId) {
  const startTime = Date.now();
  const outputDir = path.join(config.uploadDir, 'pptx-to-image', jobId);

  // Ensure output directory exists
  await fs.mkdir(outputDir, { recursive: true });

  try {
    // Stage 1: Convert PPTX to PDF
    console.log(`Job ${jobId}: Converting to PDF...`);
    const pdfPath = await convertToPdf(inputPath, outputDir);

    // Stage 2: Convert PDF to images
    console.log(`Job ${jobId}: Converting PDF to images...`);
    const images = await convertPdfToImages(pdfPath, outputDir, 'slide');

    // Clean up intermediate PDF
    await fs.unlink(pdfPath).catch(() => {});

    const processingTime = Date.now() - startTime;
    console.log(`Job ${jobId}: Successfully created ${images.length} images in ${processingTime}ms`);

    return {
      success: true,
      images,
      slideCount: images.length,
      processingTimeMs: processingTime,
    };
  } catch (error) {
    console.error(`Job ${jobId}: Conversion failed - ${error.message}`);
    return {
      success: false,
      images: [],
      slideCount: 0,
      error: error.message,
      processingTimeMs: Date.now() - startTime,
    };
  }
}

/**
 * Convert PDF to images
 */
async function convertPdfToImagesJob(inputPath, jobId) {
  const startTime = Date.now();
  const outputDir = path.join(config.uploadDir, 'pdf-to-image', jobId);

  // Ensure output directory exists
  await fs.mkdir(outputDir, { recursive: true });

  try {
    console.log(`Job ${jobId}: Converting PDF to images...`);
    const images = await convertPdfToImages(inputPath, outputDir, 'page');

    const processingTime = Date.now() - startTime;
    console.log(`Job ${jobId}: Successfully created ${images.length} images in ${processingTime}ms`);

    return {
      success: true,
      images,
      slideCount: images.length,
      processingTimeMs: processingTime,
    };
  } catch (error) {
    console.error(`Job ${jobId}: Conversion failed - ${error.message}`);
    return {
      success: false,
      images: [],
      slideCount: 0,
      error: error.message,
      processingTimeMs: Date.now() - startTime,
    };
  }
}

module.exports = {
  convertPptxToImages,
  convertPdfToImagesJob,
};
