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
        
        # Face detection - use DNN if available, fallback to Haar Cascade
        self.face_detector = None
        self.use_dnn = False
        self._init_face_detector()

        self._load_model()
    
    def _init_face_detector(self) -> None:
        """Initialize face detector - prefer DNN over Haar Cascade for better accuracy."""
        if not CV2_AVAILABLE:
            return
            
        try:
            # Try to use OpenCV DNN face detector (more accurate for multiple faces)
            # Check if we have the model files
            dnn_proto = cv2.data.haarcascades.replace('haarcascades', '') + "deploy.prototxt"
            dnn_model = cv2.data.haarcascades.replace('haarcascades', '') + "res10_300x300_ssd_iter_140000.caffemodel"
            
            if os.path.exists(dnn_proto) and os.path.exists(dnn_model):
                self.face_detector = cv2.dnn.readNetFromCaffe(dnn_proto, dnn_model)
                self.use_dnn = True
                logger.info("✅ Using DNN face detector (more accurate)")
            else:
                # Fallback to Haar Cascade
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
                    import torch  # type: ignore[import-not-found]
                    self.model = torch.load(self.model_path)
                    self.model.eval()
                    logger.info("✅ Loaded PyTorch model")
                except ImportError:
                    logger.warning("Neither TensorFlow nor PyTorch available")
        except FileNotFoundError:
            logger.warning(f"Model file not found: {self.model_path}. Using mock predictions.")
        except Exception as e:
            logger.error(f"Failed to load model: {e}. Using mock predictions.")

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
            
            # Use multiple cascades for better detection
            face_cascade_default = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            face_cascade_alt = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_alt.xml'
            )
            face_cascade_alt2 = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_alt2.xml'
            )
            
            # ✅ Try multiple detectors and use the one that finds the most faces
            all_faces = []
            
            # Detector 1: Default with lenient params
            faces1 = face_cascade_default.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=3, minSize=(30, 30)
            )
            if len(faces1) > 0:
                all_faces.append(('default', faces1))
            
            # Detector 2: Alt cascade (better for profile/angled faces)
            faces2 = face_cascade_alt.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=3, minSize=(30, 30)
            )
            if len(faces2) > 0:
                all_faces.append(('alt', faces2))
            
            # Detector 3: Alt2 cascade
            faces3 = face_cascade_alt2.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=3, minSize=(30, 30)
            )
            if len(faces3) > 0:
                all_faces.append(('alt2', faces3))
            
            # Use the detector that found the MOST faces (catches multiple people)
            if all_faces:
                best_detector, faces = max(all_faces, key=lambda x: len(x[1]))
                face_count = len(faces)
                logger.info(f"🔍 Best detector '{best_detector}': {face_count} face(s) found")
            else:
                # Try even more lenient as last resort
                faces = face_cascade_default.detectMultiScale(
                    gray, scaleFactor=1.05, minNeighbors=2, minSize=(20, 20)
                )
                face_count = len(faces)
                logger.info(f"🔍 Lenient detection: {face_count} face(s) found")
            
            # Check for multiple faces FIRST - this is the priority
            if face_count > 1:
                logger.warning(f"⚠️ MULTIPLE FACES DETECTED: {face_count} people in frame!")
                return 'multiple_faces', None, face_count
            
            # Single face found
            if face_count == 1:
                x, y, w, h = faces[0]
                face_roi = gray[y:y+h, x:x+w]
                logger.debug(f"Single face detected: {w}x{h} at ({x},{y})")
                return 'single_face', face_roi, 1
            
            logger.debug("No face detected in frame")
            return 'no_face', None, 0

        except Exception as e:
            logger.error(f"Face detection error: {e}")
            return 'error', None, 0

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
            
            logger.info(f"📷 Processing frame: {image.shape}")

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
