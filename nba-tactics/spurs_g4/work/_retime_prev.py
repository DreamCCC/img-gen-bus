"""_retime_prev.py <out.jpg> <img> [img...]: tile full frames 3 per row (960 wide), red box = HUD zone x>1470, y<260."""
import sys

import cv2
import numpy as np

tiles = []
for p in sys.argv[2:]:
    im = cv2.imread(p)
    cv2.rectangle(im, (1470, 0), (1919, 260), (0, 0, 255), 3)
    t = cv2.resize(im, (960, 540), interpolation=cv2.INTER_AREA)
    cv2.putText(t, p.replace("\\", "/").split("/")[-1], (8, 530), 0, 0.8, (0, 255, 255), 2)
    tiles.append(t)
while len(tiles) % 3:
    tiles.append(np.zeros_like(tiles[0]))
cv2.imwrite(sys.argv[1], np.vstack([np.hstack(tiles[i:i + 3]) for i in range(0, len(tiles), 3)]), [cv2.IMWRITE_JPEG_QUALITY, 85])
print(sys.argv[1])
