# Product Requirements Document: Media Converter Service

**Version:** 1.0
**Status:** Draft
**Last Updated:** 2026-01-15

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Goals & Objectives](#3-goals--objectives)
4. [Target Users](#4-target-users)
5. [User Stories](#5-user-stories)
6. [Functional Requirements](#6-functional-requirements)
7. [Non-Functional Requirements](#7-non-functional-requirements)
8. [System Constraints](#8-system-constraints)
9. [Success Metrics](#9-success-metrics)
10. [Scope & Phasing](#10-scope--phasing)
11. [Risks & Dependencies](#11-risks--dependencies)
12. [Appendix](#appendix)

---

## 1. Executive Summary

**Media Converter** is a self-hosted media transformation service designed to convert files between formats without relying on third-party paid APIs. The service provides a simple REST API that accepts file uploads, processes them locally using open-source tools, and returns transformed output.

**Phase 1 Focus:** PPTX-to-Image conversion module — converting PowerPoint presentations into high-fidelity slide images.

### Key Value Propositions

| Value | Description |
|-------|-------------|
| **Cost Control** | No per-conversion fees; fixed infrastructure costs only |
| **Data Privacy** | Files never leave your infrastructure |
| **Customization** | Full control over output quality, formats, and processing |
| **Integration** | Simple REST API for easy integration with existing systems |

---

## 2. Problem Statement

### Current Pain Points

Organizations frequently need to convert PowerPoint presentations to images for various purposes:

1. **Web Publishing** — Embedding presentation slides in web pages without requiring PowerPoint viewers
2. **Thumbnail Generation** — Creating preview images for document management systems
3. **Social Media** — Converting slides for sharing on platforms that don't support PPTX
4. **Archival** — Preserving presentations in a universally accessible format
5. **PDF Generation Workflows** — Using images as intermediate format for custom PDF layouts

### Existing Solutions & Their Limitations

| Solution | Limitation |
|----------|------------|
| **Cloud APIs (CloudConvert, Zamzar)** | Per-conversion costs; data leaves your control |
| **Microsoft Graph API** | Requires Microsoft 365 subscription; complex auth |
| **Manual Conversion** | Not scalable; requires user intervention |
| **Client-side Libraries** | Limited fidelity; can't handle complex formatting |

### The Gap

There is no simple, self-hosted, cost-effective solution for automated PPTX-to-Image conversion that:
- Handles both legacy `.ppt` and modern `.pptx` formats
- Preserves complex formatting, fonts, and layouts
- Provides a clean API for integration
- Requires no ongoing subscription costs

---

## 3. Goals & Objectives

### Primary Goal

Deliver a reliable, self-hosted API service that converts PowerPoint files to high-quality images with minimal operational overhead.

### Objectives

| ID | Objective | Success Indicator |
|----|-----------|-------------------|
| O1 | **High Fidelity** | Output images visually match source slides (>95% accuracy) |
| O2 | **Simple Integration** | Single API endpoint with <10 lines of client code |
| O3 | **Reliable Processing** | >99% success rate for valid input files |
| O4 | **Reasonable Performance** | Process 10-slide deck in <30 seconds |
| O5 | **Easy Deployment** | Single `docker-compose up` to run |
| O6 | **Zero External Dependencies** | No paid SaaS, no external API calls |

### Non-Goals (Out of Scope for Phase 1)

- Real-time collaborative editing
- PPTX creation or modification
- Animation or video extraction from presentations
- User authentication/authorization (assumed to be handled by API gateway)
- Multi-tenant isolation
- Billing or usage tracking

---

## 4. Target Users

### Primary Users

#### 4.1 Backend Developers

**Profile:** Engineers integrating document conversion into existing applications

**Needs:**
- Clean, well-documented REST API
- Predictable response formats
- Error handling guidance
- Code examples in common languages

**Usage Pattern:** Programmatic API calls from backend services

---

#### 4.2 DevOps Engineers

**Profile:** Operations staff responsible for deploying and maintaining the service

**Needs:**
- Docker-based deployment
- Clear resource requirements
- Health check endpoints
- Logging and monitoring hooks
- Simple configuration via environment variables

**Usage Pattern:** Deploy, configure, monitor, scale

---

#### 4.3 Product Managers / Internal Tools Teams

**Profile:** Non-technical stakeholders who need conversion capabilities for internal tools

**Needs:**
- Reliable, "just works" service
- No per-use costs to track
- Reasonable processing speed

**Usage Pattern:** Indirect users via applications built on the API

---

### User Personas

```
┌─────────────────────────────────────────────────────────────────┐
│  PERSONA: Alex the API Integrator                               │
│                                                                 │
│  Role: Senior Backend Developer                                 │
│  Company: SaaS platform for sales enablement                    │
│                                                                 │
│  Goal: Allow customers to upload pitch decks and automatically  │
│        generate shareable slide galleries                       │
│                                                                 │
│  Pain: Current solution (CloudConvert) costs $500/month and     │
│        requires sending customer data to third party            │
│                                                                 │
│  Success: Self-hosted solution with simple API, <5 min setup    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  PERSONA: Jordan the DevOps Engineer                            │
│                                                                 │
│  Role: Platform Engineer                                        │
│  Company: Enterprise with strict data governance                │
│                                                                 │
│  Goal: Deploy document conversion that keeps data on-premise    │
│                                                                 │
│  Pain: Security team rejected cloud-based solutions;            │
│        existing on-prem tools are complex to maintain           │
│                                                                 │
│  Success: Docker container that "just works" with standard      │
│           monitoring stack (Prometheus, Grafana)                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. User Stories

### Epic: PPTX to Image Conversion

#### US-001: Basic Conversion (MVP)

**As a** backend developer
**I want to** upload a PPTX file and receive images for each slide
**So that** I can display presentation content in my web application

**Acceptance Criteria:**
- [ ] POST endpoint accepts multipart file upload
- [ ] Supports both `.ppt` and `.pptx` formats
- [ ] Returns JSON array of image URLs/paths
- [ ] Each slide produces exactly one image
- [ ] Images are named sequentially (slide_001.jpg, slide_002.jpg, etc.)

---

#### US-002: Synchronous Processing

**As a** developer building a simple integration
**I want to** send a file and wait for the converted images in the same request
**So that** I don't need to implement polling logic for small files

**Acceptance Criteria:**
- [ ] `wait=true` parameter (default) blocks until conversion completes
- [ ] Response includes all image paths upon completion
- [ ] Timeout after configurable duration (default 5 minutes)
- [ ] Clear error message if conversion fails

---

#### US-003: Asynchronous Processing

**As a** developer handling large presentations
**I want to** submit a conversion job and poll for status
**So that** I can handle long-running conversions without HTTP timeouts

**Acceptance Criteria:**
- [ ] `wait=false` parameter returns immediately with job ID
- [ ] Status endpoint returns current job state
- [ ] Status includes progress indicator (0-100%)
- [ ] Completed status includes image paths

---

#### US-004: File Size Limits

**As a** system administrator
**I want to** configure maximum upload file size
**So that** I can prevent resource exhaustion from oversized files

**Acceptance Criteria:**
- [ ] Configurable max file size via environment variable
- [ ] Uploads exceeding limit rejected with 413 status code
- [ ] Clear error message indicating the limit
- [ ] Default limit: 100MB

---

#### US-005: Image Quality Configuration

**As a** developer
**I want to** configure output image DPI and format
**So that** I can balance quality vs file size for my use case

**Acceptance Criteria:**
- [ ] Configurable DPI (default: 200)
- [ ] Configurable format (JPEG or PNG)
- [ ] Configurable JPEG quality (default: 90%)
- [ ] Settings applied consistently across all conversions

---

#### US-006: Health Monitoring

**As a** DevOps engineer
**I want to** check service health via an endpoint
**So that** I can integrate with monitoring and load balancers

**Acceptance Criteria:**
- [ ] GET /health returns service status
- [ ] Response indicates if dependencies (LibreOffice, Poppler) are available
- [ ] Returns appropriate HTTP status (200 healthy, 503 unhealthy)
- [ ] Response time <1 second

---

#### US-007: Error Handling

**As a** developer
**I want to** receive clear error messages when conversion fails
**So that** I can debug issues and provide feedback to users

**Acceptance Criteria:**
- [ ] Invalid file type returns 400 with specific error
- [ ] Corrupt file returns 400 with descriptive message
- [ ] Conversion timeout returns 500 with timeout indication
- [ ] All errors include job_id for tracing

---

#### US-008: Concurrent Processing

**As a** developer with multiple simultaneous users
**I want the** service to handle concurrent requests
**So that** one slow conversion doesn't block others

**Acceptance Criteria:**
- [ ] Service handles 5+ concurrent conversions
- [ ] Each conversion runs in isolation
- [ ] No file collisions between jobs
- [ ] Configurable worker pool size

---

### Future User Stories (Post-MVP)

| ID | Story | Priority |
|----|-------|----------|
| US-009 | Webhook notifications on job completion | Medium |
| US-010 | Batch conversion (multiple files in one request) | Medium |
| US-011 | Custom output dimensions (resize images) | Low |
| US-012 | Selective slide conversion (specific page ranges) | Low |
| US-013 | Watermark support | Low |
| US-014 | PDF output option (PPTX → PDF) | Medium |

---

## 6. Functional Requirements

### FR-001: File Upload

| Attribute | Specification |
|-----------|---------------|
| **Endpoint** | `POST /api/v1/convert/pptx-to-image` |
| **Content-Type** | `multipart/form-data` |
| **File Field** | `file` |
| **Supported Formats** | `.ppt`, `.pptx` |
| **Max File Size** | Configurable (default 100MB) |

### FR-002: Conversion Output

| Attribute | Specification |
|-----------|---------------|
| **Output Location** | `uploads/pptx-to-image/{job_id}/slide_{NNN}.{ext}` |
| **Naming Convention** | Zero-padded 3-digit index (001, 002, ...) |
| **Image Format** | JPEG (default) or PNG |
| **Default DPI** | 200 |
| **Default Quality** | 90% (JPEG only) |

### FR-003: API Response Format

**Success Response (200 OK):**
```json
{
  "job_id": "uuid",
  "status": "completed",
  "message": "Successfully converted N slides",
  "total_slides": 5,
  "images": [
    "/uploads/pptx-to-image/{job_id}/slide_001.jpg",
    "/uploads/pptx-to-image/{job_id}/slide_002.jpg"
  ],
  "processing_time_ms": 3450
}
```

**Error Response (4xx/5xx):**
```json
{
  "error": "ErrorType",
  "detail": "Human-readable description",
  "job_id": "uuid (if applicable)"
}
```

### FR-004: Job Status Endpoint

| Attribute | Specification |
|-----------|---------------|
| **Endpoint** | `GET /api/v1/convert/status/{job_id}` |
| **Status Values** | `pending`, `processing`, `completed`, `failed` |
| **Progress** | 0-100 percentage |

### FR-005: Static File Serving

| Attribute | Specification |
|-----------|---------------|
| **Base Path** | `/uploads/` |
| **Access** | Direct HTTP GET |
| **Retention** | Configurable TTL (default 24 hours) |

### FR-006: Health Check

| Attribute | Specification |
|-----------|---------------|
| **Endpoint** | `GET /health` |
| **Response** | Service status, dependency availability |

---

## 7. Non-Functional Requirements

### NFR-001: Performance

| Metric | Target |
|--------|--------|
| **Throughput** | Process 5 concurrent 10-slide decks |
| **Latency (10 slides)** | < 30 seconds |
| **Latency (single slide)** | < 5 seconds |
| **API Response Time** | < 100ms (excluding conversion) |

### NFR-002: Reliability

| Metric | Target |
|--------|--------|
| **Success Rate** | > 99% for valid input files |
| **Graceful Degradation** | Return partial results on timeout |
| **Error Recovery** | Service auto-recovers from worker crashes |

### NFR-003: Scalability

| Metric | Target |
|--------|--------|
| **Horizontal Scaling** | Stateless API supports multiple instances |
| **Vertical Scaling** | Performance scales with worker count |
| **Migration Path** | Architecture supports Redis/Celery migration |

### NFR-004: Security

| Requirement | Implementation |
|-------------|----------------|
| **File Validation** | Verify file headers, not just extension |
| **Path Traversal** | Sanitize all file paths |
| **Resource Limits** | Enforce file size and timeout limits |
| **Process Isolation** | Workers run as non-root user |
| **No Secrets in Logs** | File contents never logged |

### NFR-005: Maintainability

| Requirement | Implementation |
|-------------|----------------|
| **Logging** | Structured JSON logs with request correlation |
| **Configuration** | All settings via environment variables |
| **Documentation** | OpenAPI spec auto-generated |
| **Testability** | Modular design with dependency injection |

### NFR-006: Deployment

| Requirement | Implementation |
|-------------|----------------|
| **Containerization** | Single Docker image with all dependencies |
| **Orchestration** | docker-compose for local development |
| **Health Checks** | Kubernetes-compatible health/ready endpoints |
| **Resource Limits** | CPU/memory limits configurable |

---

## 8. System Constraints

### 8.1 Technical Constraints

| Constraint | Rationale |
|------------|-----------|
| **Python 3.11+** | Required for modern async features |
| **Docker Required** | LibreOffice/Poppler system dependencies |
| **Linux-based Container** | LibreOffice headless support |
| **x86_64 Architecture** | Primary target (ARM64 possible but untested) |

### 8.2 Business Constraints

| Constraint | Rationale |
|------------|-----------|
| **No Paid APIs** | Cost control, data sovereignty |
| **No Complex Message Brokers** | Operational simplicity for low traffic |
| **Open Source Only** | License compliance, vendor independence |

### 8.3 Resource Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| **CPU** | 2 cores | 4 cores |
| **Memory** | 2 GB | 4 GB |
| **Disk** | 10 GB | 50 GB (depends on retention) |
| **Network** | Standard | Standard |

---

## 9. Success Metrics

### 9.1 Adoption Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Integration Time** | < 1 hour | Time from docker pull to first successful API call |
| **API Simplicity** | < 10 LOC | Lines of code for basic integration |

### 9.2 Operational Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Conversion Success Rate** | > 99% | Successful conversions / Total attempts |
| **P95 Latency (10 slides)** | < 30s | 95th percentile processing time |
| **Availability** | > 99.5% | Uptime excluding planned maintenance |

### 9.3 Quality Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Visual Fidelity** | > 95% | Manual review of sample conversions |
| **Format Coverage** | 100% | Support for both .ppt and .pptx |

---

## 10. Scope & Phasing

### Phase 1: PPTX-to-Image MVP (Current)

**Deliverables:**
- [x] Technical Design Document
- [x] Product Requirements Document
- [ ] Core conversion service (PptxConverter)
- [ ] REST API endpoints
- [ ] Docker deployment configuration
- [ ] Basic documentation

**Capabilities:**
- PPTX/PPT to JPEG/PNG conversion
- Synchronous and asynchronous processing modes
- Configurable output quality
- Health monitoring endpoint

---

### Phase 2: Operational Maturity

**Deliverables:**
- [ ] Prometheus metrics endpoint
- [ ] Structured JSON logging
- [ ] Automatic job cleanup
- [ ] Admin endpoint for job management

**Capabilities:**
- Production-grade observability
- Self-healing job management
- Operational dashboards

---

### Phase 3: Extended Conversions

**Deliverables:**
- [ ] DOCX-to-PDF converter
- [ ] XLSX-to-PDF converter
- [ ] PDF-to-Image converter
- [ ] Unified conversion API

**Capabilities:**
- Multiple document format support
- Consistent API across formats

---

### Phase 4: Scale & Enterprise Features

**Deliverables:**
- [ ] Redis/Celery backend option
- [ ] Webhook notifications
- [ ] Batch processing API
- [ ] Rate limiting

**Capabilities:**
- Horizontal scaling
- Enterprise-grade throughput
- Integration with event-driven architectures

---

### Feature Roadmap Matrix

| Feature | Phase 1 | Phase 2 | Phase 3 | Phase 4 |
|---------|:-------:|:-------:|:-------:|:-------:|
| PPTX → Image | ✅ | ✅ | ✅ | ✅ |
| Sync/Async modes | ✅ | ✅ | ✅ | ✅ |
| Health checks | ✅ | ✅ | ✅ | ✅ |
| Prometheus metrics | | ✅ | ✅ | ✅ |
| Job cleanup | | ✅ | ✅ | ✅ |
| DOCX → PDF | | | ✅ | ✅ |
| XLSX → PDF | | | ✅ | ✅ |
| PDF → Image | | | ✅ | ✅ |
| Redis/Celery | | | | ✅ |
| Webhooks | | | | ✅ |
| Batch API | | | | ✅ |

---

## 11. Risks & Dependencies

### 11.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| LibreOffice rendering inconsistencies | Medium | Medium | Test with diverse PPTX samples; maintain font packages |
| Memory exhaustion with large files | Low | High | Enforce file size limits; configure resource limits |
| LibreOffice process hangs | Medium | Medium | Implement timeouts; worker process isolation |
| Poppler version incompatibilities | Low | Low | Pin versions in Dockerfile |

### 11.2 Operational Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Disk space exhaustion | Medium | Medium | Implement automatic cleanup; monitoring alerts |
| Concurrent job overload | Medium | Medium | Bounded worker pool; queue management |
| Container image size | Low | Low | Multi-stage builds; cleanup apt cache |

### 11.3 Dependencies

| Dependency | Type | Risk Level | Fallback |
|------------|------|------------|----------|
| LibreOffice | System | Low | Well-maintained OSS project |
| Poppler | System | Low | Well-maintained OSS project |
| FastAPI | Python | Low | Stable, widely adopted |
| pdf2image | Python | Low | Thin wrapper, easy to replace |

---

## Appendix

### A. Glossary

| Term | Definition |
|------|------------|
| **Job** | A single conversion request with unique identifier |
| **Worker** | Background process executing conversions |
| **DPI** | Dots per inch; image resolution setting |
| **Headless** | Running without graphical user interface |

### B. Reference Documents

| Document | Location |
|----------|----------|
| Technical Design Document | `docs/design/PPTX_TO_IMAGE_DESIGN.md` |
| API Specification | `/docs` endpoint (auto-generated) |

### C. API Quick Reference

```bash
# Convert PPTX to images (synchronous)
curl -X POST "http://localhost:8000/api/v1/convert/pptx-to-image" \
  -F "file=@presentation.pptx"

# Convert PPTX to images (asynchronous)
curl -X POST "http://localhost:8000/api/v1/convert/pptx-to-image?wait=false" \
  -F "file=@presentation.pptx"

# Check job status
curl "http://localhost:8000/api/v1/convert/status/{job_id}"

# Health check
curl "http://localhost:8000/health"
```

### D. Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | development | Environment mode |
| `MAX_WORKERS` | 3 | Concurrent conversion workers |
| `MAX_FILE_SIZE_MB` | 100 | Maximum upload size |
| `IMAGE_DPI` | 200 | Output image resolution |
| `IMAGE_FORMAT` | JPEG | Output format (JPEG/PNG) |
| `JPEG_QUALITY` | 90 | JPEG compression quality |
| `JOB_TIMEOUT_SECONDS` | 300 | Max conversion time |
| `JOB_TTL_HOURS` | 24 | Job retention period |

---

*Document End*
