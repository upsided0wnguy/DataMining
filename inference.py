import numpy as np
import torch
import rasterio
from PIL import Image
import io, base64

MEAN = np.array([637.189342, 871.552721, 772.949392, 1985.648665], dtype=np.float32)
STD  = np.array([263.729817, 277.694238, 351.328225, 1025.712170], dtype=np.float32)

PATCH_SIZE = 256

CLASS_COLORS = np.array([
    [0,   114, 189, 180],   # Water      — blue
    [56,  168,   0, 180],   # Trees      — green
    [220,  50,  32, 180],   # Buildings  — red
    [230, 210, 120, 180],   # Open Land  — yellow
], dtype=np.uint8)

CLASS_NAMES = ["Water", "Trees", "Buildings", "Open Land"]


def load_image(file_bytes: bytes, filename: str) -> np.ndarray:
    """Load 4-band image from uploaded file bytes. Returns (H, W, 4) float32."""
    if filename.endswith(".npy"):
        img = np.load(io.BytesIO(file_bytes)).astype(np.float32)
        if img.ndim == 3 and img.shape[0] == 4:
            img = img.transpose(1, 2, 0)
    else:
        with rasterio.open(io.BytesIO(file_bytes)) as src:
            img = src.read().astype(np.float32).transpose(1, 2, 0)
    return img


def normalize(img: np.ndarray) -> np.ndarray:
    return (img - MEAN) / STD


def predict_patch(model, patch: np.ndarray, device: str) -> np.ndarray:
    """Predict single 256x256 patch. Returns (256,256) int class mask."""
    norm  = normalize(patch)
    tensor = torch.from_numpy(norm.transpose(2, 0, 1)).unsqueeze(0).to(device)
    with torch.no_grad():
        logits = model(tensor)
    return logits.argmax(dim=1).squeeze(0).cpu().numpy().astype(np.uint8)


def predict_full_image(model, img: np.ndarray, device: str) -> np.ndarray:
    """
    Run inference on any size image using sliding window (256x256, stride 256).
    Returns full-size class mask (H, W).
    """
    H, W, _ = img.shape
    mask = np.zeros((H, W), dtype=np.uint8)
    count = np.zeros((H, W), dtype=np.uint8)

    for y in range(0, H, PATCH_SIZE):
        for x in range(0, W, PATCH_SIZE):
            y2 = min(y + PATCH_SIZE, H)
            x2 = min(x + PATCH_SIZE, W)
            patch = np.zeros((PATCH_SIZE, PATCH_SIZE, 4), dtype=np.float32)
            ph, pw = y2 - y, x2 - x
            patch[:ph, :pw] = img[y:y2, x:x2]
            pred = predict_patch(model, patch, device)
            mask[y:y2, x:x2] = pred[:ph, :pw]
            count[y:y2, x:x2] += 1

    return mask


def mask_to_rgba(mask: np.ndarray) -> np.ndarray:
    """Convert class mask to RGBA image array."""
    H, W = mask.shape
    rgba = np.zeros((H, W, 4), dtype=np.uint8)
    for c in range(4):
        rgba[mask == c] = CLASS_COLORS[c]
    return rgba


def img_to_base64(arr: np.ndarray, mode="RGBA") -> str:
    """Convert numpy array to base64 PNG string."""
    pil = Image.fromarray(arr, mode=mode)
    buf = io.BytesIO()
    pil.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def rgb_preview(img: np.ndarray) -> str:
    """Return base64 RGB preview of the satellite image (bands B4,B3,B2)."""
    rgb = img[:, :, [2, 1, 0]].copy()
    # simple percentile stretch for display
    for c in range(3):
        p2, p98 = np.percentile(rgb[:, :, c], [2, 98])
        rgb[:, :, c] = np.clip((rgb[:, :, c] - p2) / (p98 - p2 + 1e-6) * 255, 0, 255)
    return img_to_base64(rgb.astype(np.uint8), mode="RGB")
