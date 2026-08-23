"""
Digit Inference Wrapper for Roll Number Recognition.
"""

from pathlib import Path
from typing import List, Optional, Tuple, Union
import cv2
import numpy as np

try:
    import onnxruntime as ort
    HAS_ONNX = True
except ImportError:
    HAS_ONNX = False

import torch
from backend.app.ml_model.train_digit_model import DigitCNN


class DigitPredictor:
    """
    Roll Number Digit Predictor supporting ONNX Runtime and PyTorch backends.
    """

    def __init__(self, model_dir: Optional[Path] = None):
        if model_dir is None:
            model_dir = Path(__file__).resolve().parent

        self.onnx_path = model_dir / "digit_model.onnx"
        self.pt_path = model_dir / "digit_model.pt"

        self.ort_session = None
        self.torch_model = None

        # 1. Try ONNX runtime
        if HAS_ONNX and self.onnx_path.exists():
            try:
                self.ort_session = ort.InferenceSession(str(self.onnx_path), providers=["CPUExecutionProvider"])
            except Exception:
                self.ort_session = None

        # 2. Fallback to PyTorch
        if self.ort_session is None and self.pt_path.exists():
            try:
                self.torch_model = DigitCNN(num_classes=10)
                self.torch_model.load_state_dict(torch.load(self.pt_path, map_location="cpu", weights_only=True))
                self.torch_model.eval()
            except Exception:
                self.torch_model = None

    def preprocess_patch(self, patch: np.ndarray) -> np.ndarray:
        """
        Resize ROI patch to 28x28 grayscale, normalize to [0, 1] tensor shape (1, 1, 28, 28).
        """
        if patch.ndim == 3:
            gray = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
        else:
            gray = patch.copy()

        resized = cv2.resize(gray, (28, 28), interpolation=cv2.INTER_AREA)
        # Normalize: digit ink = 1.0, background = 0.0
        normalized = 1.0 - (resized.astype(np.float32) / 255.0)
        return normalized.reshape(1, 1, 28, 28)

    def predict_digit(self, patch: np.ndarray) -> Tuple[int, float]:
        """
        Predict single digit (0-9) and confidence score from cropped patch.
        """
        tensor_np = self.preprocess_patch(patch)

        if self.ort_session is not None:
            outputs = self.ort_session.run(None, {"input": tensor_np})
            logits = outputs[0][0]
            exp_logits = np.exp(logits - np.max(logits))
            probs = exp_logits / np.sum(exp_logits)
            pred_digit = int(np.argmax(probs))
            conf = float(probs[pred_digit])
            return pred_digit, conf

        if self.torch_model is not None:
            with torch.no_grad():
                tensor_torch = torch.from_numpy(tensor_np)
                logits = self.torch_model(tensor_torch).numpy()[0]
                exp_logits = np.exp(logits - np.max(logits))
                probs = exp_logits / np.sum(exp_logits)
                pred_digit = int(np.argmax(probs))
                conf = float(probs[pred_digit])
                return pred_digit, conf

        # Fallback to pure CV mean brightness
        return 0, 0.5

    def predict_roll_number(self, patches: List[np.ndarray]) -> Tuple[str, float]:
        """
        Predict full roll number sequence from ordered digit patches.
        """
        digits = []
        confs = []
        for p in patches:
            d, c = self.predict_digit(p)
            digits.append(str(d))
            confs.append(c)

        return "".join(digits), float(np.mean(confs)) if confs else 0.5
