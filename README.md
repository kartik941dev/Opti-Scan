# OptiScan - Full-Stack Automated OMR Grading & Psychometric Analytics Platform

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI%200.109+-009688.svg)](https://fastapi.tiangolo.com/)
[![React + Vite](https://img.shields.io/badge/Frontend-React%2018%20(Vite)-61DAFB.svg)](https://vitejs.dev/)
[![CI/CD](https://github.com/kartik941dev/Opti-Scan/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/kartik941dev/Opti-Scan/actions/workflows/ci-cd.yml)
[![OpenCV](https://img.shields.io/badge/Computer%20Vision-OpenCV%204.8+-5C3EE8.svg)](https://opencv.org/)
[![PyTorch](https://img.shields.io/badge/ML%20Digits-PyTorch%20%2F%20ONNX-EE4C2C.svg)](https://pytorch.org/)
[![MongoDB](https://img.shields.io/badge/Database-MongoDB%20%2F%20Motor-47A248.svg)](https://www.mongodb.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**OptiScan** is a full-stack automated OMR grading and psychometric analytics platform. It leverages **OpenCV** for computer vision OMR processing and an integrated **PyTorch CNN** for roll-number digit recognition. It replaces legacy, proprietary hardware optical scanners by processing standard flatbed scanner scans and casual smartphone captures (JPG, PNG, TIFF, PDF) using high-speed Computer Vision, automatic 4-point homography perspective warp, adaptive ink-density calibration, roll-number digit recognition, and Classical Test Theory (CTT) item diagnostics.

### 🔄 End-to-End Workflow

```
Image → OpenCV preprocessing → Perspective correction → Bubble detection → Adaptive fill detection → Answer extraction → CNN roll-number recognition → Grading → Psychometric Analysis
```

---

## 🔬 Technical Workflow

The OptiScan grading engine executes a high-throughput, 12-stage computer vision and machine learning pipeline:

1. **Image Validation & Ingestion**: Validates file integrity and decodes raster image streams (JPG, PNG, TIFF) or extracts PDF pages into high-resolution pixel matrices via PyMuPDF/OpenCV.
2. **Preprocessing**: Normalizes dimensions and converts the input sheet into standardized grayscale for matrix processing.
3. **Contrast Enhancement & Noise Reduction**: Applies Contrast Limited Adaptive Histogram Equalization (CLAHE) and bilateral filtering to eliminate shadows, paper creases, scanner artifacts, and non-uniform lighting.
4. **Fiducial Detection**: Locates 4 corner registration / fiducial marker targets using contour filtering, bounding box geometry, and aspect ratio verification.
5. **Homography Perspective Correction**: Orders the detected fiducials (TL, TR, BR, BL) and computes a 4-point perspective warp matrix to rectify skewed, rotated, or casual mobile camera captures into canonical template coordinates.
6. **Bubble-Grid Mapping**: Projects the standardized 100-question coordinate blueprint and roll number grid onto the rectified canvas.
7. **Adaptive Fill Detection**: Crops circular bubble Regions of Interest (ROIs), applies circular erosion masks to isolate pencil/pen markings from bubble borders, and dynamically calibrates ink density thresholds against ambient page illumination.
8. **CNN Roll-Number Recognition**: Crops student ID digit patch cells, normalizes each 28×28 pixel patch, and passes them to the **PyTorch / ONNX Convolutional Neural Network (DigitCNN)** for digit inference and confidence scoring.
9. **Answer-Key Comparison & Scoring**: Matches candidate responses against exam blueprint keys, applying section-based weights, custom positive/negative rules, bonus allocations, and multi-mark penalty handling.
10. **Psychometric Analysis**: Aggregates batch-level metrics including Item Difficulty Index ($P$), Item Discrimination Index ($D$), distractor distribution counts, and Kuder-Richardson Formula 20 ($KR\text{-}20$) test reliability.
11. **Visual Audit Generation**: Generates annotated verification overlays marking correct choices in green, incorrect choices in red, and missing selections for educator transparency.
12. **PDF & Multi-Tab Excel Export**: Compiles graded rosters, student breakdown cards, and item diagnostic summaries into downloadable ReportLab PDFs and multi-tab Excel sheets.

---

## 💡 Why OpenCV + Deep Learning?

OptiScan pairs classical computer vision with deep learning based on the nature of each sub-task:

- **Deterministic Computer Vision (OpenCV)**: Standardized OMR sheets have fixed fiducial markers and strictly defined geometry. Classical CV techniques (CLAHE contrast normalization, bilateral filtering, 4-point homography perspective warp, and circular erosion masking) deliver deterministic, zero-hallucination bubble detection and ink-density calculation with sub-millisecond execution and no GPU requirements.
- **Deep Learning (PyTorch CNN)**: Candidate roll-number digits exhibit variations in fonts, stroke thickness, slight positional offsets, and noise. A lightweight Convolutional Neural Network handles character pattern recognition to classify digits (0–9) and produce confidence scores.

---

## 🧠 Roll-Number Digit Recognition Model (DigitCNN)

The roll-number recognition module is implemented in [`backend/app/ml_model/train_digit_model.py`](backend/app/ml_model/train_digit_model.py) and [`backend/app/ml_model/predict_roll_number.py`](backend/app/ml_model/predict_roll_number.py):

- **Model Architecture**:
  - **Feature Extractor**: 3 Convolutional Blocks
    - Block 1: `Conv2d(1, 16, 3x3, pad=1)` → `BatchNorm2d(16)` → `ReLU` → `MaxPool2d(2, 2)` (outputs $14 \times 14$)
    - Block 2: `Conv2d(16, 32, 3x3, pad=1)` → `BatchNorm2d(32)` → `ReLU` → `MaxPool2d(2, 2)` (outputs $7 \times 7$)
    - Block 3: `Conv2d(32, 64, 3x3, pad=1)` → `BatchNorm2d(64)` → `ReLU` → `AdaptiveAvgPool2d((3, 3))` (outputs $3 \times 3$)
  - **Classifier**: `Flatten` → `Linear(576, 64)` → `ReLU` → `Dropout(0.25)` → `Linear(64, 10)` (outputs logits for digits `0–9`).
- **Input & Normalization**: $28 \times 28$ grayscale patches resized and inverted so digit ink values are normalized to $[0.0, 1.0]$ ($1 \times 1 \times 28 \times 28$).
- **Training Setup**:
  - **Dataset**: `SyntheticDigitDataset` generating procedural digit samples across OpenCV Hershey font variants with randomized scale ($0.6$–$0.9$), thickness ($1$–$3$), affine rotations ($\pm 15^\circ$), and Gaussian noise ($\sigma = 8$).
  - **Loss Function**: `nn.CrossEntropyLoss()`
  - **Optimizer**: `optim.Adam(lr=0.003)`
  - **Schedule**: 12 epochs with batch size 64.
- **Inference Pipeline (`DigitPredictor`)**:
  - Primary execution via **ONNX Runtime** (`digit_model.onnx` on `CPUExecutionProvider`).
  - Native fallback to **PyTorch** (`digit_model.pt` on CPU) when ONNX runtime is not present.
  - Softmax calculation providing per-digit class prediction and confidence metric.

---

## 🏛️ System Architecture

```
                                 [OptiScan Platform]
                                          │
                  ┌───────────────────────┴───────────────────────┐
                  ▼                                               ▼
         [Frontend Web App]                              [Backend REST API]
     (React 18 + Vite + Recharts)                      (FastAPI + Uvicorn + MongoDB)
                  │                                               │
      • Responsive Educator UI                        • JWT Authentication & RBAC
      • Drag & Drop Batch Upload                      • Exams & Answer Key Blueprints
      • Visual Audit Sheet Modal                      • OMR Pure-CV Computer Vision Pipeline
      • Real-time Psychometrics                       • PyTorch Digit Recognition Model
      • Printable PDF Downloader                      • Multi-Tab Excel & PDF Scorecards
```

---

## 📁 Repository Structure

```
├── frontend/                     # React (Vite) Single-Page Application (SPA)
│   ├── src/
│   │   ├── api/                  # Axios API client bindings
│   │   ├── components/           # Sidebar, Navbar, MetricCard, SheetViewerModal
│   │   ├── context/              # Auth & JWT state
│   │   ├── pages/                # Dashboard, Exams, AnswerKey, Evaluate, Analytics, PrintTemplates
│   │   ├── index.css             # Glassmorphism design system
│   │   └── App.jsx
│   ├── package.json
│   └── vite.config.js
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI application entrypoint
│   │   ├── config.py             # Settings, directories, and CORS config
│   │   ├── routes/               # auth.py, exams.py, answer_key.py, omr_upload.py, results.py
│   │   ├── omr_engine/           # Pure Computer Vision OMR Engine
│   │   │   ├── preprocess.py     # Grayscale, CLAHE contrast, bilateral denoise, adaptive mask
│   │   │   ├── align.py          # 4-point fiducial detection & homography perspective warp
│   │   │   ├── bubble_grid.py    # Standard 100Q coordinate geometry mapping
│   │   │   ├── detect_fill.py    # Circular erosion mask & adaptive fill threshold calibration
│   │   │   └── grade.py          # Scoring engine (+4/-1, Bonus, Sections) & visual audit generator
│   │   ├── ml_model/             # Roll Number Digit Recognition
│   │   │   ├── train_digit_model.py # Lightweight CNN training script
│   │   │   ├── digit_model.pt    # PyTorch trained model weights
│   │   │   └── predict_roll_number.py # Roll number prediction wrapper
│   │   └── db/                   # MongoDB Persistence Layer (with In-Memory Fallback)
│   │       ├── mongo.py          # Async Motor connection manager & fallback
│   │       └── models.py         # Pydantic / MongoDB schemas
│   ├── templates/
│   │   └── omr_template.json     # Standard 100Q layout coordinate template
│   └── requirements.txt          # Python backend dependencies
├── templates_design/             # Printable OMR Sheet Designer & Vector Assets
│   ├── generate_printable_omr.py # Procedural vector A4 printable sheet generator
│   └── standard_100q_omr.pdf     # Production-ready 100Q printable OMR form
└── README.md
```

---

## ⚡ Quick Start Guide

### 1. Prerequisites
- **Python 3.10+** (Tested on Python 3.13)
- **Node.js 18+** & **npm**
- *(Optional)* **MongoDB** (A built-in resilient in-memory database fallback is enabled by default if MongoDB is not running locally).

---

### 2. Backend Setup & Startup

```bash
# Navigate to project root
cd OPtiscan

# Install Python backend dependencies
pip install -r backend/requirements.txt

# Launch FastAPI backend server (Port 8000)
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend API Swagger documentation will be available at: **[http://localhost:8000/docs](http://localhost:8000/docs)**

---

### 3. Frontend Setup & Startup

```bash
# Navigate to frontend folder
cd frontend

# Install npm dependencies
npm install

# Start Vite React dev server (Port 5173)
npm run dev
```

Open your browser at: **[http://localhost:5173](http://localhost:5173)**

---

## 🔑 Demo Credentials

Credentials and authentication settings are configured through environment variables. For local setup and development templates, refer to the [`.env.example`](.env.example) file.

---

## 🖨️ Printable OMR Sheet Generation

Generate customized high-resolution vector printable A4 exam sheets:

```bash
python templates_design/generate_printable_omr.py
```
Output: `templates_design/standard_100q_omr.pdf`

---

## 📊 Psychometric Item Diagnostics (Classical Test Theory)

OptiScan implements psychometric analytics directly in [`backend/app/routes/results.py`](backend/app/routes/results.py) based on Classical Test Theory (CTT):

- **Difficulty Index ($P$):** Proportion of candidates answering each question correctly:
  $$P = \frac{N_{\text{correct}}}{N_{\text{total}}}$$
  Categorized as **Hard** ($P < 0.30$), **Moderate** ($0.30 \le P \le 0.70$), or **Easy** ($P > 0.70$).
- **Discrimination Index ($D$):** Ability of an item to distinguish high-performing candidates from low-performing candidates using the Kelly 27% method ($N_{\text{group}} = \text{round}(0.27 \times N)$):
  $$D = \frac{R_{\text{upper 27\%}} - R_{\text{lower 27\%}}}{N_{\text{group}}}$$
  Categorized as **Excellent** ($D \ge 0.40$), **Good** ($0.20 \le D < 0.40$), **Marginal** ($0.0 \le D < 0.20$), or **Flawed** ($D < 0.0$).
- **Distractor Analysis:** Detailed selection frequencies per item across individual options (A, B, C, D), unattempted (Blank), and multiple-marked invalid attempts.
- **Exam Reliability ($KR\text{-}20$):** Kuder-Richardson Formula 20 measuring overall test internal consistency:
  $$KR\text{-}20 = \left(\frac{K}{K-1}\right) \left(1 - \frac{\sum p_i q_i}{\sigma^2_{\text{total}}}\right)$$
  where $K$ is the item count, $p_i$ is item difficulty, $q_i = 1 - p_i$, and $\sigma^2_{\text{total}}$ is the total score variance (computed when $N \ge 5$).

---

## 📈 Verified Benchmarks & Performance

Measured via automated test suites (`test_standalone.py` and `test_digit_model.py`):

| Stage / Component | Measured Metric | Details |
| :--- | :--- | :--- |
| **Digit CNN Recognition** | **99.60% Accuracy** | 498/500 correct on a held-out test set; 61,098 trainable parameters |
| **Preprocessing & Denoise** | **~70 ms** | Bilateral filter + CLAHE + Adaptive Gaussian thresholding |
| **Homography Alignment** | **~34 ms** | 4-point corner fiducial detection and perspective rectification |
| **Bubble Extraction & Fill** | **~17 ms** | 100 questions (400 bubbles) + 60 digit bubbles evaluated |
| **Scoring & Section Aggregation** | **< 1 ms** | Vectorized score calculation & section breakdown |
| **Visual Audit Overlay** | **~10 ms** | Color-coded transparent verification overlay generation |

---

## 👤 Author

Developed by **Kartik** ([@kartik941dev](https://github.com/kartik941dev))

---

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.
