from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import torch, os, traceback
import numpy as np

from model           import load_model
from inference       import load_image, predict_full_image, mask_to_rgba, img_to_base64, rgb_preview
from livability      import compute_livability
from change_detection import compute_change
from report          import generate_report

# ── setup ──────────────────────────────────────────────────
app = FastAPI(title="Livability Assessment API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MODEL_PATH = os.path.join(os.path.dirname(__file__), "best_model.pth")

print(f"Device: {DEVICE}")

model = None

def get_model():
    global model
    if model is None:
        if not os.path.exists(MODEL_PATH):
            raise HTTPException(
                status_code=500,
                detail="best_model.pth not found. Place it in the backend/ folder."
            )
        print("Loading model...")
        model = load_model(MODEL_PATH, DEVICE)
        print("Model loaded.")
    return model


# ── routes ─────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status" : "ok",
        "device" : DEVICE,
        "model"  : os.path.exists(MODEL_PATH),
    }


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    """
    Upload a single 4-band GeoTIFF or .npy satellite image.
    Returns segmentation mask, livability score, zone, area stats.
    """
    try:
        m = get_model()
        raw_bytes = await file.read()

        img  = load_image(raw_bytes, file.filename)
        mask = predict_full_image(m, img, DEVICE)

        rgba        = mask_to_rgba(mask)
        overlay_b64 = img_to_base64(rgba, mode="RGBA")
        preview_b64 = rgb_preview(img)
        livability  = compute_livability(mask)

        return {
            "status"          : "ok",
            "filename"        : file.filename,
            "image_shape"     : list(img.shape[:2]),
            "preview_b64"     : preview_b64,
            "overlay_b64"     : overlay_b64,
            "livability"      : livability,
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/compare")
async def compare(
    file_2017: UploadFile = File(...),
    file_2025: UploadFile = File(...),
):
    """
    Upload two 4-band images (2017 and 2025).
    Returns change detection overlay + area deltas + alerts.
    """
    try:
        m = get_model()

        bytes_2017 = await file_2017.read()
        bytes_2025 = await file_2025.read()

        img_2017 = load_image(bytes_2017, file_2017.filename)
        img_2025 = load_image(bytes_2025, file_2025.filename)

        # resize 2017 to match 2025 if needed
        H, W = img_2025.shape[:2]
        if img_2017.shape[:2] != (H, W):
            from PIL import Image
            import io
            # simple nearest resize via PIL
            for_resize = img_2017[:,:,0]
            ratio_h = H / img_2017.shape[0]
            ratio_w = W / img_2017.shape[1]
            new_h = H
            new_w = W
            img_2017_resized = np.zeros((new_h, new_w, 4), dtype=np.float32)
            for c in range(4):
                band = img_2017[:, :, c]
                pil  = Image.fromarray(band).resize((new_w, new_h), Image.BILINEAR)
                img_2017_resized[:, :, c] = np.array(pil)
            img_2017 = img_2017_resized

        mask_2017 = predict_full_image(m, img_2017, DEVICE)
        mask_2025 = predict_full_image(m, img_2025, DEVICE)

        change       = compute_change(mask_2017, mask_2025)
        change_rgba  = change.pop("change_rgba")

        overlay_2017_b64 = img_to_base64(mask_to_rgba(mask_2017), mode="RGBA")
        overlay_2025_b64 = img_to_base64(mask_to_rgba(mask_2025), mode="RGBA")
        change_b64       = img_to_base64(change_rgba, mode="RGBA")
        preview_2017_b64 = rgb_preview(img_2017)
        preview_2025_b64 = rgb_preview(img_2025)

        livability_2017 = compute_livability(mask_2017)
        livability_2025 = compute_livability(mask_2025)

        return {
            "status"          : "ok",
            "preview_2017_b64": preview_2017_b64,
            "preview_2025_b64": preview_2025_b64,
            "overlay_2017_b64": overlay_2017_b64,
            "overlay_2025_b64": overlay_2025_b64,
            "change_b64"      : change_b64,
            "livability_2017" : livability_2017,
            "livability_2025" : livability_2025,
            "change"          : change,
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/report")
async def download_report(file: UploadFile = File(...)):
    """Generate and return a PDF report for a single image."""
    try:
        m           = get_model()
        raw_bytes   = await file.read()
        img         = load_image(raw_bytes, file.filename)
        mask        = predict_full_image(m, img, DEVICE)
        livability  = compute_livability(mask)
        pdf_bytes   = generate_report(livability)

        return Response(
            content     = pdf_bytes,
            media_type  = "application/pdf",
            headers     = {"Content-Disposition": "attachment; filename=livability_report.pdf"},
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
