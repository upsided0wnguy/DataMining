import torch
import segmentation_models_pytorch as smp

NUM_CLASSES  = 4
IN_CHANNELS  = 4
ENCODER      = "efficientnet-b4"

def build_model(device="cpu"):
    model = smp.UnetPlusPlus(
        encoder_name    = ENCODER,
        encoder_weights = None,        # no pretrained needed at inference
        in_channels     = IN_CHANNELS,
        classes         = NUM_CLASSES,
        activation      = None,
    )
    return model.to(device)


def load_model(checkpoint_path: str, device="cpu"):
    model = build_model(device)
    checkpoint = torch.load(checkpoint_path, map_location=device)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()
    return model
