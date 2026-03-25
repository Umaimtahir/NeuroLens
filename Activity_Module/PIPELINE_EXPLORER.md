# NeuroLens: Activity Classification Pipeline

The Activity Module uses a **7-Stage "Aggressive Inference" Pipeline** designed to be fast (<1.5s), accurate, and context-aware.

## 🏗️ The 7-Stage Pipeline

### Stage 1: Behavioral Check (The "Senses")
- **Detection**: Mouse/keyboard movement, CPU load, and background apps.
- **Role**: Detects if your teammate is "Idle" or doing something in the background (like listening to Spotify or downloading a file).

### Stage 2: Heuristic Engine (The "Fast Path")
- **Detection**: Process names (e.g., `code.exe`) and Window Titles.
- **Role**: If it sees "Visual Studio Code" or "YouTube", it classifies it **instantly** (0ms) without using the AI models.

### Stage 3: CLIP (The "Visual Gate")
- **Model**: `openai/clip-vit-base-patch32`
- **Role**: A fast visual check. It looks at a low-res (224x224) version of the screen to identify broad categories like "Coding", "Social Media", or "Gaming".

### Stage 4: Florence-2 OCR (The "Reader")
- **Model**: `microsoft/Florence-2-base`
- **Role**: If visuals aren't enough, it "reads" the actual text on the screen. It extracts code snippets, document headers, or website names.

### Stage 5: OCR Heuristics (The "Context Filter")
- **Role**: Re-runs the heuristic engine on the text found by Florence-2. If it finds keywords like `def`, `interface`, or `add to cart`, it finalizes the label here.

### Stage 6: Florence-2 Captioning (The "Observer")
- **Model**: `microsoft/Florence-2-base`
- **Role**: It describes the scene in plain English (e.g., *"A web browser showing a research paper with diagrams"*).

### Stage 7: Qwen2.5 Reasoning (The "Brain")
- **Model**: `Qwen/Qwen2.5-0.5B-Instruct`
- **Role**: The final decision-maker. It takes the Window Title + OCR Text + Visual Caption and "reasons" to pick the most accurate category from the taxonomy.

---

## 🛠️ Summary of Model Roles

| Model | Role | Analogy |
| :--- | :--- | :--- |
| **CLIP** | Broad Visual Category | "A quick glance" |
| **Florence-2** | OCR & Visual Description | "Reading the details" |
| **Qwen2.5** | High-level Reasoning | "Thinking about the context" |

## 🔄 Temporal & Multi-label Logic
- **Smoothing**: It keeps a buffer of recent activities so a 1-second focus switch doesn't "jitter" the results.
- **Fusion**: It can detect multiple things at once (e.g., **"Coding + Background Music"**).
