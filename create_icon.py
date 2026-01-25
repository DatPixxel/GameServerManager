"""
Erstellt das App-Icon für Game Server Manager Pro
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_icon():
    """Erstellt ein modernes Gaming-Icon"""
    
    # Verschiedene Größen für .ico
    sizes = [16, 32, 48, 64, 128, 256]
    images = []
    
    for size in sizes:
        # Erstelle Bild mit transparentem Hintergrund
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Hintergrund-Gradient simulieren (dunkelblau zu schwarz)
        for y in range(size):
            # Gradient von #1a1a2e zu #0f0f1a
            r = int(26 - (y / size) * 11)
            g = int(26 - (y / size) * 11)
            b = int(46 - (y / size) * 20)
            for x in range(size):
                # Runde Ecken
                center = size / 2
                radius = size / 2 - 1
                dist = ((x - center) ** 2 + (y - center) ** 2) ** 0.5
                if dist <= radius:
                    draw.point((x, y), fill=(r, g, b, 255))
        
        # Äußerer Glow-Ring (cyan)
        ring_width = max(1, size // 16)
        for angle in range(360):
            import math
            rad = math.radians(angle)
            for r_offset in range(ring_width):
                r = (size / 2 - 2 - r_offset)
                x = int(size / 2 + r * math.cos(rad))
                y = int(size / 2 + r * math.sin(rad))
                if 0 <= x < size and 0 <= y < size:
                    # Cyan Glow
                    alpha = int(255 * (1 - r_offset / ring_width) * 0.7)
                    current = img.getpixel((x, y))
                    new_color = (0, 212, 255, max(current[3], alpha))
                    draw.point((x, y), fill=new_color)
        
        # Innerer Kreis (grün für "aktiv")
        inner_radius = size // 4
        center = size // 2
        draw.ellipse(
            [center - inner_radius, center - inner_radius,
             center + inner_radius, center + inner_radius],
            fill=(0, 255, 136, 255)  # #00ff88
        )
        
        # Play-Symbol (Dreieck)
        triangle_size = inner_radius * 0.8
        offset = inner_radius * 0.15  # Leicht nach rechts versetzt für optische Mitte
        
        # Dreieck-Punkte
        p1 = (center - triangle_size/2 + offset, center - triangle_size/2)  # Oben links
        p2 = (center - triangle_size/2 + offset, center + triangle_size/2)  # Unten links
        p3 = (center + triangle_size/2 + offset, center)  # Rechts Mitte
        
        draw.polygon([p1, p2, p3], fill=(26, 26, 46, 255))  # Dunkler Hintergrund
        
        images.append(img)
    
    # Speichere als .ico
    icon_path = os.path.join(os.path.dirname(__file__), "gsm_icon.ico")
    images[0].save(
        icon_path,
        format='ICO',
        sizes=[(s, s) for s in sizes],
        append_images=images[1:]
    )
    print(f"✅ Icon erstellt: {icon_path}")
    
    # Auch als PNG für andere Zwecke
    png_path = os.path.join(os.path.dirname(__file__), "gsm_icon.png")
    images[-1].save(png_path, format='PNG')
    print(f"✅ PNG erstellt: {png_path}")
    
    return icon_path

if __name__ == "__main__":
    create_icon()
