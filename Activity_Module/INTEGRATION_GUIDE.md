# Integration Guide: Activity Module

This guide helps you integrate the **NeuroLens Activity Classifier** into your part of the FYP.

## 1. Running as a Service (Recommended)
The easiest way to use this module is to run it as a standalone background service and call its API.

### Endpoint: `POST /classify/title`
Use this for instant classification when you only have the window title.
- **Request Body**: `{"window_title": "string"}`
- **Latency**: < 10ms

### Endpoint: `POST /analyze/activity`
Use this for the full AI pipeline (Visual + Title analysis).
- **Behavior**: The server will capture the active window screen itself.
- **Latency**: 0.5s - 1.5s (requires GPU for best speed).

## 2. Integration via Python
If your project is also in Python, you can import the engine directly:

```python
from activity_classifier.classifier import ActivityClassifier

# Initialize
classifier = ActivityClassifier()

# Run full pipeline
result = classifier.run_pipeline()
print(f"Detected: {result.label} ({result.confidence})")
```

## 3. Collaboration via Git
To work together on this:
1. Initialize a Git repository in this folder.
2. Push to a private GitHub/GitLab repository.
3. Add your team member as a collaborator.
4. **Important**: Ensure `.gitignore` is present to avoid pushing the `.venv` folder.

## 4. Hardware Requirements
- **Minimum**: 8GB RAM.
- **Recommended**: NVIDIA GPU with 4GB+ VRAM (CUDA-enabled) for real-time visual analysis.
- **CPU-only**: Works, but visual analysis `/analyze/activity` will be slower.
