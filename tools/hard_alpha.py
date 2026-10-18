"""Snap alpha to 0/255 so GIF's 1-bit transparency drops faint glows instead of dithering them into speckles.

    python3 tools/hard_alpha.py <dir of PNG frames> <alpha cutoff 0-255>    # edits the frames in place
"""
import sys, glob
import numpy as np
from PIL import Image
for f in sorted(glob.glob(sys.argv[1] + '/*.png')):
    a = np.asarray(Image.open(f).convert('RGBA')).copy()
    keep = a[:, :, 3] >= int(sys.argv[2])
    a[:, :, 3] = np.where(keep, 255, 0)
    Image.fromarray(a).save(f)
