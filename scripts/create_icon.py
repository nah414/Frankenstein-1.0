#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Icon Creator
Creates a proper monster icon for the desktop shortcut
"""

import sys
import os
from pathlib import Path

def install_pillow():
    """Install Pillow if not available"""
    try:
        from PIL import Image, ImageDraw
        return True
    except ImportError:
        print("[*] Installing Pillow for icon creation...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow", "--quiet"])
        return True

def create_monster_icon():
    """Create a multi-resolution monster icon"""
    install_pillow()
    from PIL import Image, ImageDraw
    
    # Create multiple sizes for Windows ICO
    sizes = [16, 24, 32, 48, 64, 128, 256]
    all_images = []
    
    for size in sizes:
        # Create image with dark background
        img = Image.new('RGBA', (size, size), (25, 25, 25, 255))
        draw = ImageDraw.Draw(img)
        
        # Scale factor
        s = size / 64.0
        
        # Main face - green circle/square
        margin = int(4 * s)
        face_color = (34, 139, 34, 255)  # Forest green
        face_outline = (0, 100, 0, 255)  # Dark green
        
        # Draw rounded rectangle for face
        draw.rounded_rectangle(
            [margin, margin, size - margin, size - margin],
            radius=int(8 * s),
            fill=face_color,
            outline=face_outline,
            width=max(1, int(2 * s))
        )
        
        # Flat top of head
        draw.rectangle(
            [margin + int(4*s), margin, size - margin - int(4*s), margin + int(10*s)],
            fill=face_color
        )
        
        # Eyes - white circles with green-yellow glow
        eye_radius = int(8 * s)
        eye_y = int(22 * s)
        left_eye_x = int(22 * s)
        right_eye_x = int(42 * s)
        
        # Left eye
        draw.ellipse(
            [left_eye_x - eye_radius, eye_y - eye_radius,
             left_eye_x + eye_radius, eye_y + eye_radius],
            fill=(255, 255, 200, 255),
            outline=(200, 200, 0, 255)
        )
        # Left pupil
        pupil_r = int(3 * s)
        draw.ellipse(
            [left_eye_x - pupil_r, eye_y - pupil_r,
             left_eye_x + pupil_r, eye_y + pupil_r],
            fill=(0, 0, 0, 255)
        )
        
        # Right eye
        draw.ellipse(
            [right_eye_x - eye_radius, eye_y - eye_radius,
             right_eye_x + eye_radius, eye_y + eye_radius],
            fill=(255, 255, 200, 255),
            outline=(200, 200, 0, 255)
        )
        # Right pupil
        draw.ellipse(
            [right_eye_x - pupil_r, eye_y - pupil_r,
             right_eye_x + pupil_r, eye_y + pupil_r],
            fill=(0, 0, 0, 255)
        )
        
        # Stitches/scars across forehead
        stitch_y = int(12 * s)
        stitch_color = (80, 80, 80, 255)
        line_w = max(1, int(1.5 * s))
        
        # Horizontal scar
        draw.line(
            [(int(18*s), stitch_y), (int(46*s), stitch_y)],
            fill=stitch_color, width=line_w
        )
        # Vertical stitches
        for x in range(int(20*s), int(46*s), int(6*s)):
            draw.line(
                [(x, stitch_y - int(3*s)), (x, stitch_y + int(3*s))],
                fill=stitch_color, width=line_w
            )
        
        # Mouth - stitched closed
        mouth_y = int(42 * s)
        mouth_left = int(20 * s)
        mouth_right = int(44 * s)
        
        # Main mouth line
        draw.line(
            [(mouth_left, mouth_y), (mouth_right, mouth_y)],
            fill=(50, 50, 50, 255), width=max(1, int(2*s))
        )
        # Vertical stitches on mouth
        for x in range(mouth_left, mouth_right + 1, int(6*s)):
            draw.line(
                [(x, mouth_y - int(4*s)), (x, mouth_y + int(4*s))],
                fill=(50, 50, 50, 255), width=line_w
            )
        
        # Neck bolts - Frankenstein signature
        bolt_w = int(6 * s)
        bolt_h = int(4 * s)
        bolt_y = int(32 * s)
        bolt_color = (150, 150, 150, 255)
        bolt_outline = (100, 100, 100, 255)
        
        # Left bolt
        draw.ellipse(
            [margin - int(2*s), bolt_y - bolt_h,
             margin + bolt_w, bolt_y + bolt_h],
            fill=bolt_color, outline=bolt_outline
        )
        
        # Right bolt
        draw.ellipse(
            [size - margin - bolt_w, bolt_y - bolt_h,
             size - margin + int(2*s), bolt_y + bolt_h],
            fill=bolt_color, outline=bolt_outline
        )
        
        all_images.append(img)
    
    # Save path
    assets_dir = Path(__file__).parent.parent / "assets"
    assets_dir.mkdir(exist_ok=True)
    icon_path = assets_dir / "frankenstein.ico"
    
    # Save as ICO with all sizes
    # Use the largest image as base and append others
    all_images[-1].save(
        str(icon_path),
        format='ICO',
        sizes=[(img.width, img.height) for img in all_images]
    )
    
    print(f"[OK] Monster icon created: {icon_path}")
    print(f"     Sizes: {[img.size[0] for img in all_images]}")
    print(f"     File size: {icon_path.stat().st_size} bytes")
    
    return str(icon_path)


if __name__ == "__main__":
    try:
        icon_path = create_monster_icon()
        print(f"\n[SUCCESS] Icon ready at: {icon_path}")
    except Exception as e:
        print(f"[ERROR] Failed to create icon: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
