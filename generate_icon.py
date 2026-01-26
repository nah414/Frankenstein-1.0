"""
FRANKENSTEIN 1.0 - Icon Generator
Creates a monster-themed icon for the desktop launcher

Uses Pillow to create a simple icon with the monster/Frankenstein theme.
"""

import os
import sys

def create_icon():
    """Create the FRANKENSTEIN icon"""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Pillow not installed. Install with: pip install pillow")
        return False
    
    # Icon sizes for .ico file (Windows standard sizes)
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    
    # Create the largest size, we'll resize for others
    size = 256
    
    # Create image with dark background
    img = Image.new('RGBA', (size, size), (12, 12, 12, 255))  # Dark background
    draw = ImageDraw.Draw(img)
    
    # Draw a stylized monster/Frankenstein face
    # Green face base
    face_color = (152, 195, 121)  # Green from our color scheme
    bolt_color = (225, 192, 123)  # Yellow/gold for lightning bolts
    dark_color = (30, 30, 30)
    
    # Face rectangle (Frankenstein's flat top head)
    face_margin = 40
    draw.rounded_rectangle(
        [face_margin, face_margin + 20, size - face_margin, size - face_margin],
        radius=20,
        fill=face_color
    )
    
    # Flat top of head
    draw.rectangle(
        [face_margin, face_margin, size - face_margin, face_margin + 60],
        fill=face_color
    )
    
    # Neck bolts (iconic Frankenstein's monster)
    bolt_radius = 12
    # Left bolt
    draw.ellipse(
        [face_margin - 15, 140, face_margin + 15, 140 + 40],
        fill=bolt_color,
        outline=dark_color,
        width=2
    )
    # Right bolt
    draw.ellipse(
        [size - face_margin - 15, 140, size - face_margin + 15, 140 + 40],
        fill=bolt_color,
        outline=dark_color,
        width=2
    )
    
    # Eyes
    eye_y = 100
    eye_size = 25
    left_eye_x = 90
    right_eye_x = 166
    
    # Eye whites
    draw.ellipse(
        [left_eye_x - eye_size, eye_y - eye_size, left_eye_x + eye_size, eye_y + eye_size],
        fill=(255, 255, 255)
    )
    draw.ellipse(
        [right_eye_x - eye_size, eye_y - eye_size, right_eye_x + eye_size, eye_y + eye_size],
        fill=(255, 255, 255)
    )
    
    # Pupils (looking slightly menacing)
    pupil_size = 12
    draw.ellipse(
        [left_eye_x - pupil_size, eye_y - pupil_size + 3, left_eye_x + pupil_size, eye_y + pupil_size + 3],
        fill=dark_color
    )
    draw.ellipse(
        [right_eye_x - pupil_size, eye_y - pupil_size + 3, right_eye_x + pupil_size, eye_y + pupil_size + 3],
        fill=dark_color
    )
    
    # Stitches on forehead
    stitch_y = 65
    for x in range(70, 190, 30):
        draw.line([(x, stitch_y - 8), (x, stitch_y + 8)], fill=dark_color, width=3)
    draw.line([(70, stitch_y), (186, stitch_y)], fill=dark_color, width=2)
    
    # Mouth (slight grimace)
    mouth_y = 170
    draw.arc(
        [80, mouth_y - 20, 176, mouth_y + 30],
        start=0, end=180,
        fill=dark_color,
        width=4
    )
    
    # Lightning bolt behind (representing the "alive" spark)
    # Small lightning bolt in top right corner
    bolt_points = [
        (200, 15),   # top
        (185, 50),   # mid-left
        (200, 45),   # mid
        (180, 85),   # bottom
        (195, 50),   # back up
        (210, 55),   # right
    ]
    draw.polygon(bolt_points, fill=bolt_color, outline=(200, 160, 80))
    
    # Save as ICO file with multiple sizes
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up one level if we're in scripts/
    if os.path.basename(script_dir) == 'scripts':
        project_dir = os.path.dirname(script_dir)
    else:
        project_dir = script_dir
    
    assets_dir = os.path.join(project_dir, 'assets')
    os.makedirs(assets_dir, exist_ok=True)
    
    icon_path = os.path.join(assets_dir, 'frankenstein.ico')
    
    # Create resized versions
    images = []
    for s in sizes:
        resized = img.resize(s, Image.Resampling.LANCZOS)
        images.append(resized)
    
    # Save as .ico
    img.save(icon_path, format='ICO', sizes=[(s[0], s[1]) for s in sizes])
    
    print(f"✅ Icon created: {icon_path}")
    return True


def main():
    print("⚡ FRANKENSTEIN Icon Generator")
    print("=" * 40)
    
    if create_icon():
        print("\nIcon generated successfully!")
        print("The monster icon is ready for your desktop shortcut.")
    else:
        print("\nIcon generation failed.")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
