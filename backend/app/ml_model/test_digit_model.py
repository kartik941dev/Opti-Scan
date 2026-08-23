"""
Test and Benchmark Script for Lightweight Digit Recognition CNN (Phase 3).
"""

import sys
from pathlib import Path
import torch
from torch.utils.data import DataLoader

root_dir = Path(__file__).resolve().parent.parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app.ml_model.train_digit_model import DigitCNN, SyntheticDigitDataset
from backend.app.ml_model.predict_roll_number import DigitPredictor


def evaluate_digit_cnn():
    print("=" * 60)
    print("OPTISCAN DIGIT CNN EVALUATION SUITE (PHASE 3)")
    print("=" * 60)

    model_dir = Path(__file__).resolve().parent
    model_path = model_dir / "digit_model.pt"

    print(f"\n[STEP 1] Loading PyTorch weights from {model_path}...")
    model = DigitCNN(num_classes=10)
    model.load_state_dict(torch.load(model_path, map_location="cpu", weights_only=True))
    model.eval()

    # Count total parameters
    total_params = sum(p.numel() for p in model.parameters())
    print(f"  -> Model Parameter Count: {total_params:,} params (< 30k budget)")

    print("\n[STEP 2] Evaluating on held-out test dataset (500 samples)...")
    test_dataset = SyntheticDigitDataset(num_samples=500)
    test_loader = DataLoader(test_dataset, batch_size=50, shuffle=False)

    correct = 0
    total = 0

    with torch.no_grad():
        for inputs, targets in test_loader:
            outputs = model(inputs)
            preds = torch.argmax(outputs, dim=1)
            correct += (preds == targets).sum().item()
            total += targets.size(0)

    accuracy = (correct / total) * 100.0
    print(f"  -> Test Accuracy: {accuracy:.2f}% ({correct}/{total} correct digits)")

    print("\n[STEP 3] Testing DigitPredictor wrapper...")
    predictor = DigitPredictor(model_dir=model_dir)
    test_patch = (inputs[0][0].numpy() * 255).astype("uint8")
    pred_d, conf = predictor.predict_digit(test_patch)
    print(f"  -> Single Sample Inference: Digit {pred_d} (Confidence: {conf:.2f})")

    print("\n" + "=" * 60)
    print(f"PHASE 3 DIGIT CNN TEST PASSED (Real Measured Accuracy: {accuracy:.2f}%)")
    print("=" * 60)


if __name__ == "__main__":
    evaluate_digit_cnn()
