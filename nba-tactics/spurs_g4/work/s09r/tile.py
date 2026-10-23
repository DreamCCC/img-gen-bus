import sys
from pathlib import Path
import cv2
import numpy as np

out, cols, files = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
tiles = []
for f in files:
    t = cv2.resize(cv2.imread(f), (640, 360), interpolation=cv2.INTER_AREA)
    cv2.putText(t, Path(f).parent.parent.name + " " + Path(f).stem, (8, 350), 0, 0.8, (0, 255, 255), 2)
    tiles.append(t)
tiles += [np.zeros_like(tiles[0])] * (-len(tiles) % cols)
cv2.imwrite(out, np.vstack([np.hstack(tiles[k:k + cols]) for k in range(0, len(tiles), cols)]), [cv2.IMWRITE_JPEG_QUALITY, 85])
