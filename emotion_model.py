import logging
import os
from typing import Dict, Tuple, Optional, Any

# Optional imports
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None
    np = None

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class EmotionDetector:
    """
    Emotion detection from facial expressions.
    Supports TensorFlow/Keras or optional PyTorch model.
    Falls back to mock predictions if dependencies are missing.
    """

    def __init__(self, model_path: Optional[str] = None):
        # Default path relative to this file
        if model_path is None:
            model_path = r"E:\Semester 7\fyp project\models\emotion_detection_model.h5"
        
        self.model_path: str = os.path.abspath(model_path)
        self.model: Optional[Any] = None
        self.emotions = ['angry', 'disgust', 'fear', 'happy', 'sad', 'surprise', 'neutral']

        self._load_model()

    def _load_model(self) -> None:
        """Load a pre-trained model (TensorFlow/Keras or PyTorch)."""
        try:
            # Try TensorFlow/Keras first
            try:
                from keras.models import load_model
                self.model = load_model(self.model_path)
                logger.info("✅ Loaded Keras/TensorFlow model")
            except ImportError:
                # Fall back to PyTorch
                try:
                    import torch
                    self.model = torch.load(self.model_path)
                    self.model.eval()
                    logger.info("✅ Loaded PyTorch model")
                except ImportError:
                    logger.warning("Neither TensorFlow nor PyTorch available")
        except FileNotFoundError:
            logger.warning(f"Model file not found: {self.model_path}. Using mock predictions.")
        except Exception as e:
            logger.error(f"Failed to load model: {e}. Using mock predictions.")

    def detect_face(self, image: Any) -> Tuple[bool, Optional[Any]]:
        """Detect the largest face in an image using OpenCV."""
        if not CV2_AVAILABLE or image is None:
            logger.warning("OpenCV not available or image is None. Skipping face detection.")
            return False, None

        try:
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(48, 48)
            )
            if len(faces) == 0:
                return False, None

            # Pick the largest face
            x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
            face_roi = gray[y:y+h, x:x+w]
            return True, face_roi

        except Exception as e:
            logger.error(f"Face detection error: {e}")
            return False, None

    def predict_emotion(self, face_image: Any) -> Dict[str, Any]:
        """Predict emotion from a grayscale face image."""
        if self.model is None:
            return self._mock_prediction()

        try:
            # Preprocess for Keras/TensorFlow
            face_resized = cv2.resize(face_image, (48, 48))
            face_normalized = face_resized / 255.0
            face_reshaped = face_normalized.reshape(1, 48, 48, 1)

            predictions = self.model.predict(face_reshaped, verbose=0)[0]

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
            return self._mock_prediction()

    def _mock_prediction(self) -> Dict[str, Any]:
        """Return a random mock prediction (for testing or missing model)."""
        import random
        emotion = random.choice(self.emotions)
        return {
            'emotion': emotion,
            'intensity': round(random.uniform(0.5, 0.95), 2),
            'probabilities': {e: round(random.uniform(0.1, 0.3), 2) for e in self.emotions}
        }

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

            face_found, face_roi = self.detect_face(image)
            if not face_found:
                return {
                    'success': False,
                    'error': 'No face detected',
                    'emotion': 'unknown',
                    'intensity': 0.0
                }

            result = self.predict_emotion(face_roi)
            result.update({'success': True, 'face_detected': True})
            return result

        except Exception as e:
            logger.error(f"Frame processing error: {e}")
            return {
                'success': False,
                'error': str(e),
                'emotion': 'error',
                'intensity': 0.0
            }


# Global instance
emotion_detector = EmotionDetector()
