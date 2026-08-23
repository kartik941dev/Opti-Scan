"""
Training script for Lightweight Digit Recognition CNN (Roll Number Recognition).
"""

from pathlib import Path
import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset


class DigitCNN(nn.Module):
    """
    Ultra-lightweight CNN for 28x28 grayscale digit classification (0-9).
    Parameters: ~25k (Fast inference < 1ms).
    """

    def __init__(self, num_classes: int = 10):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, 16, kernel_size=3, padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),  # 14x14

            nn.Conv2d(16, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),  # 7x7

            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d((3, 3)),  # 3x3
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(64 * 3 * 3, 64),
            nn.ReLU(inplace=True),
            nn.Dropout(0.25),
            nn.Linear(64, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.classifier(self.features(x))


class SyntheticDigitDataset(Dataset):
    """
    Procedural synthetic digit dataset generating realistic filled/printed digits and bubbles with noise.
    """

    def __init__(self, num_samples: int = 2000):
        self.samples = []
        self.labels = []
        fonts = [
            cv2.FONT_HERSHEY_SIMPLEX,
            cv2.FONT_HERSHEY_PLAIN,
            cv2.FONT_HERSHEY_DUPLEX,
            cv2.FONT_HERSHEY_COMPLEX,
        ]

        for i in range(num_samples):
            digit = i % 10
            img = np.full((28, 28), 255, dtype=np.uint8)

            # Randomize font, scale, thickness, position
            font = fonts[np.random.randint(0, len(fonts))]
            scale = np.random.uniform(0.6, 0.9)
            thickness = np.random.randint(1, 3)

            # Draw digit
            text = str(digit)
            (tw, th), _ = cv2.getTextSize(text, font, scale, thickness)
            tx = max(2, (28 - tw) // 2 + np.random.randint(-2, 3))
            ty = max(18, (28 + th) // 2 + np.random.randint(-2, 3))
            cv2.putText(img, text, (tx, ty), font, scale, 0, thickness, cv2.LINE_AA)

            # Random perturbations (rotation, noise)
            angle = np.random.uniform(-15, 15)
            M = cv2.getRotationMatrix2D((14, 14), angle, 1.0)
            img = cv2.warpAffine(img, M, (28, 28), borderValue=255)

            noise = np.random.normal(0, 8, img.shape)
            img = np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)

            # Normalize to [0, 1] tensor (inverted: digit=1, background=0)
            tensor_img = torch.tensor(1.0 - (img.astype(np.float32) / 255.0), dtype=torch.float32).unsqueeze(0)
            self.samples.append(tensor_img)
            self.labels.append(digit)

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        return self.samples[idx], self.labels[idx]


def train_and_export(save_dir: Path):
    save_dir.mkdir(parents=True, exist_ok=True)
    pt_path = save_dir / "digit_model.pt"
    onnx_path = save_dir / "digit_model.onnx"

    dataset = SyntheticDigitDataset(num_samples=5000)
    dataloader = DataLoader(dataset, batch_size=64, shuffle=True)

    model = DigitCNN(num_classes=10)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.003)

    model.train()
    for epoch in range(12):
        total_loss = 0.0
        for inputs, targets in dataloader:
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()

    # Save PyTorch weights
    torch.save(model.state_dict(), pt_path)
    print(f"[OK] Saved trained PyTorch digit model to {pt_path}")

    # Export to ONNX (optional)
    try:
        model.eval()
        dummy_input = torch.randn(1, 1, 28, 28, dtype=torch.float32)
        torch.onnx.export(
            model,
            dummy_input,
            str(onnx_path),
            input_names=["input"],
            output_names=["output"],
            dynamic_axes={"input": {0: "batch_size"}, "output": {0: "batch_size"}},
            opset_version=14,
        )
        print(f"[OK] Exported ONNX digit model to {onnx_path}")
    except Exception as e:
        print(f"[NOTE] ONNX export skipped ({e}), PyTorch model is ready at {pt_path}")


if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parent
    train_and_export(out_dir)
