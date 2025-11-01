
import sys
from PIL import Image
import numpy as np

def extract_green_leaves(input_path: str, output_path: str):
    img = Image.open(input_path).convert("RGBA")
    arr = np.array(img)

    # Convert RGB to HSV to isolate green hues
    rgb = arr[..., :3] / 255.0
    r, g, b = rgb[...,0], rgb[...,1], rgb[...,2]
    cmax = rgb.max(axis=-1)
    cmin = rgb.min(axis=-1)
    delta = cmax - cmin

    # Hue calculation
    hue = np.zeros_like(cmax)
    mask = delta != 0
    idx = (cmax == r) & mask
    hue[idx] = (60 * ((g[idx] - b[idx]) / delta[idx]) + 360) % 360
    idx = (cmax == g) & mask
    hue[idx] = (60 * ((b[idx] - r[idx]) / delta[idx]) + 120) % 360
    idx = (cmax == b) & mask
    hue[idx] = (60 * ((r[idx] - g[idx]) / delta[idx]) + 240) % 360

    sat = np.zeros_like(cmax)
    sat[cmax != 0] = delta[cmax != 0] / cmax[cmax != 0]

    val = cmax

    # Green range (approx 70-170 degrees), with saturation/value thresholds
    green = (hue >= 70) & (hue <= 170) & (sat > 0.2) & (val > 0.25)

    # Create transparent background and keep only green parts
    out = np.zeros_like(arr)
    out[..., :3] = arr[..., :3]
    out[..., 3] = (green * 255).astype(np.uint8)

    # If result too sparse (thresholds too strict), relax slightly
    if out[...,3].sum() < 1000:
        green = (hue >= 60) & (hue <= 180) & (sat > 0.15) & (val > 0.2)
        out[..., 3] = (green * 255).astype(np.uint8)

    # Trim transparent borders and pad to square 512x512
    out_img = Image.fromarray(out, mode="RGBA")
    bbox = out_img.getbbox()
    if bbox:
        out_img = out_img.crop(bbox)

    # Make square canvas
    size = max(out_img.width, out_img.height)
    canvas = Image.new("RGBA", (size, size), (0,0,0,0))
    canvas.paste(out_img, ((size - out_img.width)//2, (size - out_img.height)//2))

    # Resize to 512x512
    canvas = canvas.resize((512, 512), Image.LANCZOS)
    canvas.save(output_path)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python extract_icon_from_logo.py <input_logo.png> <output_icon.png>")
        sys.exit(1)
    extract_green_leaves(sys.argv[1], sys.argv[2])
    print("Icon created:", sys.argv[2])
