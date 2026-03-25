# NeuroLens: Activity Classifier Module

A robust, AI-powered activity classification system designed for the NeuroLens FYP. This module captures screen context (window titles and visuals) and uses a multi-stage vision-language pipeline to categorize user activity with high precision.

## 🚀 Features
- **Zero-Shot Classification**: Uses Florence-2 and Qwen2.5 for deep reasoning.
- **Fast Heuristic Path**: Instant classification for known app signatures.
- **Hybrid Context**: Combines visual OCR/captioning with behavioral signals.
- **RESTful API**: Easily integrable with any frontend (Flutter, Web, etc.).

## 🛠️ Quick Setup

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd Activity_Module
   ```

2. **Create a Virtual Environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Service**:
   ```bash
   python main.py
   ```
   The service will start at `http://localhost:8001`.

## 📖 API Documentation
Once running, visit `http://localhost:8001/docs` for the interactive Swagger documentation.
