"""Bounded square crop coordinates shared by desktop frontends."""
def crop_box(width, height, zoom=1.0, x=0.0, y=0.0):
    """Offsets are source pixels from the image center; clamp every edge."""
    side = min(width, height) / max(1.0, min(4.0, zoom))
    left = max(0.0, min(width-side, (width-side)/2-x))
    top = max(0.0, min(height-side, (height-side)/2-y))
    return left, top, left+side, top+side
