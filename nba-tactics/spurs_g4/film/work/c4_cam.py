"""Camera framing helper for court3d.js scenes: same projection math as Court.project, prints screen coords of key points."""
import json
import math
import sys
from pathlib import Path


def project(cam, p, H=1080):
    ex, ey, ez = cam['eye']
    tx, ty, tz = cam['target']
    f = [tx - ex, ty - ey, tz - ez]
    l = math.sqrt(sum(v * v for v in f)); f = [v / l for v in f]
    r = [f[1] * 1 - f[2] * 0, f[2] * 0 - f[0] * 1, 0]
    l = math.hypot(r[0], r[1]); r = [r[0] / l, r[1] / l, 0]
    u = [r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0]]
    d = [p[0] - ex, p[1] - ey, (p[2] if len(p) > 2 else 0) - ez]
    zc = sum(a * b for a, b in zip(d, f))
    foc = (H / 2) / math.tan(math.radians(cam['fov']) / 2)
    s = foc / zc
    cx, cy = cam.get('center', [960, 540])
    return round(cx + sum(a * b for a, b in zip(d, r)) * s), round(cy - sum(a * b for a, b in zip(d, u)) * s), round(s, 1)


def main():
    scene = sys.argv[1]
    cfg = json.loads(Path(scene).read_text(encoding='utf-8'))
    pts = {p['name']: (p['x'], p['y']) for p in cfg['data']['players']}
    pts.update({'RIM_FLOOR': (41.75, 0), 'RIM': (41.75, 0, 10), 'BOARD_TOP': (43, 0, 13), 'NEAR_SL_30': (30, -25), 'FAR_SL_30': (30, 25),
                'NEAR_BL': (47, -25), 'FAR_BL': (47, 25), 'MID_NEAR': (0, -25), 'MID_FAR': (0, 25)})
    if 'tip' in cfg['data']:
        pts['TIP'] = (cfg['data']['tip']['x'], cfg['data']['tip']['y'])
    for key in sys.argv[2:] or ['cam0', 'cam1']:
        cam = cfg[key]
        print('==', key, cam)
        for k, p in pts.items():
            print(f'  {k:12s}', project(cam, p))


if __name__ == '__main__':
    main()
