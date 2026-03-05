import logging
import os
from typing import Dict, Tuple, Optional, Any, List

# Optional imports
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None
    np = None

try:
    import torch
    import torch.nn as nn
    import timm
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None
    nn = None
    timm = None

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

if TORCH_AVAILABLE:
    class _EmotionModel(nn.Module):
        """EfficientNet-B4 backbone + custom classifier (matches training checkpoint)."""
        def __init__(self, num_classes=7):
            super().__init__()
            self.backbone = timm.create_model('efficientnet_b4', pretrained=False, num_classes=0)
            self.classifier = nn.Sequential(
                nn.Dropout(0.5),
                nn.Linear(1792, 512),
                nn.ReLU(),
                nn.Dropout(0.3),
                nn.Linear(512, num_classes)
            )

        def forward(self, x):
            features = self.backbone(x)
            return self.classifier(features)
else:
    _EmotionModel = None


class EmotionDetector:
    """
    Emotion detection from facial expressions using a PyTorch EfficientNet-B4 model.
    Falls back to mock predictions if dependencies are missing.
    """

    # Max dimension for face detection (smaller = faster)
    FACE_DETECT_MAX_DIM = 320

    def __init__(self, model_path: Optional[str] = None):
        # Default path relative to this file
        if model_path is None:
            model_path = r"E:\Semester 7\fyp project\models\74.pth"
        
        self.model_path: str = os.path.abspath(model_path)
        self.model: Optional[Any] = None
        self.device = None
        self.emotions = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']
        
        # Face detection - use DNN if available, fallback to Haar Cascade
        self.face_detector = None
        self.use_dnn = False
        
        # Pre-load cascade classifiers ONCE (not per frame)
        self._cascade_default = None
        self._cascade_alt = None
        self._init_face_detector()

        self._load_model()
    
    def _init_face_detector(self) -> None:
        """Initialize face detector - prefer DNN over Haar Cascade for better accuracy."""
        if not CV2_AVAILABLE:
            return
            
        try:
            dnn_proto = cv2.data.haarcascades.replace('haarcascades', '') + "deploy.prototxt"
            dnn_model = cv2.data.haarcascades.replace('haarcascades', '') + "res10_300x300_ssd_iter_140000.caffemodel"
            
            if os.path.exists(dnn_proto) and os.path.exists(dnn_model):
                self.face_detector = cv2.dnn.readNetFromCaffe(dnn_proto, dnn_model)
                self.use_dnn = True
                logger.info("✅ Using DNN face detector (more accurate)")
            else:
                self.face_detector = cv2.CascadeClassifier(
                    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                )
                self.use_dnn = False
                logger.info("ℹ️ Using Haar Cascade face detector")
        except Exception as e:
            logger.warning(f"DNN init failed, using Haar Cascade: {e}")
            self.face_detector = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            self.use_dnn = False

        # Pre-load cascade classifiers once (reused every frame)
        try:
            self._cascade_default = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            self._cascade_alt = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_alt2.xml'
            )
            logger.info("✅ Cascade classifiers pre-loaded")
        except Exception as e:
            logger.warning(f"Failed to pre-load cascades: {e}")

    def _load_model(self) -> None:
        """Load the PyTorch EfficientNet-B4 emotion model."""
        if not TORCH_AVAILABLE:
            logger.warning("PyTorch/timm not available. Using mock predictions.")
            return

        try:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            model = _EmotionModel(num_classes=7)
            checkpoint = torch.load(self.model_path, map_location=self.device)

            if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
                model.load_state_dict(checkpoint['model_state_dict'])
            elif isinstance(checkpoint, dict) and 'state_dict' in checkpoint:
                model.load_state_dict(checkpoint['state_dict'])
            else:
                model.load_state_dict(checkpoint)

            model.to(self.device)
            model.eval()
            self.model = model
            logger.info(f"✅ Loaded PyTorch emotion model on {self.device}")
        except FileNotFoundError:
            logger.warning(f"Model file not found: {self.model_path}. Using mock predictions.")
        except Exception as e:
            logger.error(f"Failed to load model: {e}. Using mock predictions.")

    def _downscale_for_detection(self, gray: Any) -> Tuple[Any, float]:
        """Downscale image for faster face detection, return (resized, scale_factor)."""
        h, w = gray.shape[:2]
        max_dim = self.FACE_DETECT_MAX_DIM
        if max(h, w) <= max_dim:
            return gray, 1.0
        scale = max_dim / max(h, w)
        small = cv2.resize(gray, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        return small, scale

    def detect_face(self, image: Any) -> Tuple[str, Optional[Any], int]:
        """
        Detect faces in an image using OpenCV.
        Returns: (status, face_roi, face_count)
        - status: 'single_face', 'multiple_faces', 'no_face', 'error'
        - face_roi: The face region of interest (only if single face)
        - face_count: Number of faces detected
        """
        if not CV2_AVAILABLE or image is None:
            logger.warning("OpenCV not available or image is None. Skipping face detection.")
            return 'error', None, 0

        try:
            # Convert to grayscale if needed
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image

            # Downscale for faster detection
            small_gray, scale = self._downscale_for_detection(gray)
            min_face = max(20, int(30 * scale))  # scale minSize too

            # Use pre-loaded primary cascade (fast path)
            faces = self._cascade_default.detectMultiScale(
                small_gray, scaleFactor=1.1, minNeighbors=3, minSize=(min_face, min_face)
            )
            face_count = len(faces)

            # Only try secondary cascade if primary found nothing
            if face_count == 0 and self._cascade_alt is not None:
                faces = self._cascade_alt.detectMultiScale(
                    small_gray, scaleFactor=1.1, minNeighbors=3, minSize=(min_face, min_face)
                )
                face_count = len(faces)

            # Last resort: lenient params on primary
            if face_count == 0:
                min_face_lenient = max(15, int(20 * scale))
                faces = self._cascade_default.detectMultiScale(
                    small_gray, scaleFactor=1.05, minNeighbors=2, minSize=(min_face_lenient, min_face_lenient)
                )
                face_count = len(faces)

            # Check for multiple faces FIRST - this is the priority
            if face_count > 1:
                logger.warning(f"⚠️ MULTIPLE FACES DETECTED: {face_count} people in frame!")
                return 'multiple_faces', None, face_count
            
            # Single face found - map coordinates back to original image
            if face_count == 1:
                x, y, w, h = faces[0]
                # Scale back to original resolution for ROI extraction
                if scale != 1.0:
                    x = int(x / scale)
                    y = int(y / scale)
                    w = int(w / scale)
                    h = int(h / scale)
                # Clip to image bounds
                x = max(0, x)
                y = max(0, y)
                w = min(w, gray.shape[1] - x)
                h = min(h, gray.shape[0] - y)
                face_roi = gray[y:y+h, x:x+w]
                logger.debug(f"Single face detected: {w}x{h} at ({x},{y})")
                return 'single_face', face_roi, 1
            
            logger.debug("No face detected in frame")
            return 'no_face', None, 0

        except Exception as e:
            logger.error(f"Face detection error: {e}")
            return 'error', None, 0

    def predict_emotion(self, face_image: Any) -> Dict[str, Any]:
        """Predict emotion from a grayscale face image using PyTorch model."""
        if self.model is None:
            return self._mock_prediction()

        try:
            # Convert grayscale to RGB
            if len(face_image.shape) == 2:
                face_rgb = cv2.cvtColor(face_image, cv2.COLOR_GRAY2RGB)
            else:
                face_rgb = face_image

            # Resize to EfficientNet-B4 input size
            face_resized = cv2.resize(face_rgb, (380, 380))
            face_normalized = face_resized.astype(np.float32) / 255.0
            # ImageNet normalization
            mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
            std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
            face_normalized = (face_normalized - mean) / std
            # HWC -> CHW, add batch dim
            face_tensor = torch.from_numpy(face_normalized.transpose(2, 0, 1)).unsqueeze(0).to(self.device)

            with torch.no_grad():
                output = self.model(face_tensor)
                predictions = torch.softmax(output, dim=1)[0].cpu().numpy()

            emotion_idx = int(np.argmax(predictions))
            emotion = self.emotions[emotion_idx]
            intensity = float(predictions[emotion_idx])

            probabilities = {self.emotions[i]: float(predictions[i]) for i in range(len(self.emotions))}

            return {
                'emotion': emotion,
                'intensity': intensity,
                'probabilities': probabilities
            }

        except Exception as e:
            logger.error(f"Emotion prediction error: {e}")
            return self._fallback_prediction()

    def _fallback_prediction(self) -> Dict[str, Any]:
        """Return a neutral fallback prediction when model is unavailable."""
        return {
            'emotion': 'neutral',
            'intensity': 0.5,
            'probabilities': {e: 0.14 for e in self.emotions}  # Equal distribution
        }
    
    def _mock_prediction(self) -> Dict[str, Any]:
        """Alias for fallback prediction (deprecated - use _fallback_prediction)."""
        return self._fallback_prediction()
        

    def process_frame(self, frame_bytes: bytes) -> Dict[str, Any]:
        """Process a single video frame (bytes) and return emotion analysis."""
        if not CV2_AVAILABLE:
            return {
                'success': False,
                'error': 'OpenCV not installed',
                'emotion': 'unknown',
                'intensity': 0.0
            }

        try:
            nparr = np.frombuffer(frame_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                logger.error("Failed to decode image from bytes")
                return {
                    'success': False,
                    'error': 'Failed to decode image',
                    'emotion': 'unknown',
                    'intensity': 0.0
                }
            
            logger.debug(f"📷 Processing frame: {image.shape}")

            status, face_roi, face_count = self.detect_face(image)
            
            # Handle multiple faces - stop detection and return error
            if status == 'multiple_faces':
                logger.warning(f"⚠️ Multiple people detected ({face_count}). Stopping emotion detection.")
                return {
                    'success': False,
                    'error': 'multiple_faces',
                    'error_message': f'Multiple people detected ({face_count}). Please ensure only one person is in the frame.',
                    'emotion': 'error',
                    'intensity': 0.0,
                    'face_detected': True,
                    'face_count': face_count,
                    'stop_detection': True  # Signal frontend to stop and show popup
                }
            
            if status == 'no_face':
                logger.warning("⚠️ No face detected in frame")
                # Return clear "no face" response - don't guess!
                return {
                    'success': True,
                    'error': 'No face detected',
                    'emotion': 'no_face',
                    'intensity': 0.0,
                    'face_detected': False,
                    'face_count': 0
                }
            
            if status == 'error':
                return {
                    'success': False,
                    'error': 'Face detection error',
                    'emotion': 'unknown',
                    'intensity': 0.0,
                    'face_detected': False
                }

            # Single face detected - proceed with emotion prediction
            result = self.predict_emotion(face_roi)
            result.update({
                'success': True, 
                'face_detected': True,
                'face_count': 1
            })
            logger.info(f"✅ Emotion detected: {result['emotion']} ({result['intensity']:.2f})")
            return result

        except Exception as e:
            logger.error(f"Frame processing error: {e}")
            return {
                'success': False,
                'error': str(e),
                'emotion': 'neutral',
                'intensity': 0.5
            }


# Global instance
emotion_detector = EmotionDetector()
