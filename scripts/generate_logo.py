import os
import math
from pathlib import Path
from PIL import Image, ImageDraw

def create_logo():
    # Render at 1024x1024 for supersampling
    size = 1024
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Background rounded squircle
    margin = 48
    corner_radius = 220
    rect = [margin, margin, size - margin, size - margin]
    
    # Outer dark container
    draw.rounded_rectangle(rect, radius=corner_radius, fill="#13161C", outline="#252A36", width=12)

    # 2. Subtle internal glow / highlight on squircle
    inner_rect = [margin + 16, margin + 16, size - margin - 16, size - margin - 16]
    draw.rounded_rectangle(inner_rect, radius=corner_radius - 12, outline="#1D232F", width=6)

    # 3. Stylized Shield Outline & Fill (Center)
    cx, cy = size // 2, size // 2 + 10
    sw = 280  # half shield width
    sh_top = cy - 260
    sh_mid = cy + 50
    sh_bot = cy + 310

    shield_pts = [
        (cx - sw, sh_top),
        (cx + sw, sh_top),
        (cx + sw, sh_mid),
        (cx, sh_bot),
        (cx - sw, sh_mid),
    ]

    # Shield background fill with deep cyan/blue
    draw.polygon(shield_pts, fill="#162A3E", outline="#00A3E0", width=16)

    # Inner shield accent
    inner_sw = sw - 36
    inner_pts = [
        (cx - inner_sw, sh_top + 36),
        (cx + inner_sw, sh_top + 36),
        (cx + inner_sw, sh_mid - 10),
        (cx, sh_bot - 45),
        (cx - inner_sw, sh_mid - 10),
    ]
    draw.polygon(inner_pts, fill="#1B354F")

    # 4. Dynamic Sweep / Broom Arc (Clean, modern curve)
    # Draw a sweeping crescent stroke across the center
    sweep_start = (cx - 150, cy + 120)
    sweep_ctrl1 = (cx - 40, cy + 170)
    sweep_ctrl2 = (cx + 140, cy + 80)
    sweep_end = (cx + 170, cy - 80)

    # Elegant broom handle / diagonal streak
    handle_color = "#FFFFFF"
    draw.line([(cx - 130, cy + 130), (cx + 120, cy - 120)], fill=handle_color, width=32)
    # Handle cap
    draw.ellipse([cx + 105, cy - 135, cx + 135, cy - 105], fill="#00D2FF")

    # Broom bristle flare
    flare_poly = [
        (cx - 130, cy + 130),
        (cx - 200, cy + 150),
        (cx - 180, cy + 220),
        (cx - 110, cy + 180),
    ]
    draw.polygon(flare_poly, fill="#00D2FF")

    # 5. Sparkles / Stars (4-point clean diamonds)
    def draw_star(sx, sy, r, color="#FFFFFF"):
        pts = [
            (sx, sy - r),
            (sx + r * 0.28, sy - r * 0.28),
            (sx + r, sy),
            (sx + r * 0.28, sy + r * 0.28),
            (sx, sy + r),
            (sx - r * 0.28, sy + r * 0.28),
            (sx - r, sy),
            (sx - r * 0.28, sy - r * 0.28),
        ]
        draw.polygon(pts, fill=color)

    # 3 Sparkles indicating clean & active status
    draw_star(cx + 80, cy - 180, 52, "#00E5FF")
    draw_star(cx + 170, cy - 120, 36, "#FFFFFF")
    draw_star(cx - 140, cy - 80, 38, "#00B0FF")
    draw_star(cx + 130, cy + 160, 30, "#FFFFFF")

    # 6. Smooth downsampling to 512x512
    final_img = img.resize((512, 512), Image.Resampling.LANCZOS)
    
    assets_dir = Path(__file__).resolve().parent.parent / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    png_path = assets_dir / "logo.png"
    final_img.save(png_path, "PNG")
    print(f"Generated logo at: {png_path}")

    # Generate multi-resolution .ico for Windows app
    ico_path = assets_dir / "icon.ico"
    final_img.save(
        ico_path,
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    )
    print(f"Generated Windows icon at: {ico_path}")

    # Also save to artifact directory for presentation
    art_dir = Path(r"C:\Users\Zunaid\.gemini\antigravity\brain\94cf84a2-8929-4178-80c4-6fab8e5137b7")
    if art_dir.exists():
        final_img.save(art_dir / "logo.png", "PNG")

if __name__ == "__main__":
    create_logo()
