"""把 BVH 动作捕捉文件做正向运动学，导出每帧各关节的世界坐标（米，Y 轴向上）。

用法：python bvh_to_json.py in.bvh out.json [起始帧 结束帧]
"""
import json
import sys

import numpy as np

CMU_UNIT = (1.0 / 0.45) * 2.54 / 100  # CMU BVH 单位换算成米


def parse(path):
    lines = open(path).read().split("\n")
    joints, stack, i = [], [], 0
    while not lines[i].strip().startswith("MOTION"):
        tok = lines[i].split()
        if tok and tok[0] in ("ROOT", "JOINT"):
            joints.append({"name": tok[1], "parent": stack[-1] if stack else -1, "offset": None, "channels": []})
            cur = len(joints) - 1
        elif tok and tok[0] == "End":
            joints.append({"name": joints[stack[-1]]["name"] + "_End", "parent": stack[-1], "offset": None, "channels": []})
            cur = len(joints) - 1
        elif tok and tok[0] == "{":
            stack.append(cur)
        elif tok and tok[0] == "}":
            stack.pop()
        elif tok and tok[0] == "OFFSET":
            joints[cur]["offset"] = np.array(list(map(float, tok[1:4])))
        elif tok and tok[0] == "CHANNELS":
            joints[cur]["channels"] = tok[2:]
        i += 1
    n_frames = int(lines[i + 1].split()[1])
    frame_time = float(lines[i + 2].split()[2])
    data = np.array([list(map(float, l.split())) for l in lines[i + 3 : i + 3 + n_frames] if l.strip()])
    return joints, data, frame_time


def rot(axis, deg):
    a = np.radians(deg)
    c, s = np.cos(a), np.sin(a)
    return {
        "X": np.array([[1, 0, 0], [0, c, -s], [0, s, c]]),
        "Y": np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]]),
        "Z": np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]]),
    }[axis]


def fk(joints, row):
    pos, R = [None] * len(joints), [None] * len(joints)
    k = 0
    for j, jt in enumerate(joints):
        local_t, local_r = jt["offset"].copy(), np.eye(3)
        for ch in jt["channels"]:
            v = row[k]
            k += 1
            if ch.endswith("position"):
                local_t["XYZ".index(ch[0])] = v
            else:
                local_r = local_r @ rot(ch[0], v)
        if jt["parent"] < 0:
            R[j], pos[j] = local_r, local_t
        else:
            p = jt["parent"]
            R[j] = R[p] @ local_r
            pos[j] = pos[p] + R[p] @ local_t
    return np.array(pos)


def main():
    src, dst = sys.argv[1], sys.argv[2]
    joints, data, ft = parse(src)
    f0 = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    f1 = int(sys.argv[4]) if len(sys.argv) > 4 else len(data)
    frames = np.array([fk(joints, data[f]) for f in range(f0, f1)]) * CMU_UNIT
    frames[:, :, 1] -= frames[:, :, 1].min()  # 最低点贴地
    out = {
        "fps": round(1 / ft),
        "names": [j["name"] for j in joints],
        "parents": [j["parent"] for j in joints],
        "frames": np.round(frames, 4).tolist(),
    }
    json.dump(out, open(dst, "w"))
    names = out["names"]
    hips, rh, lh = names.index("Hips"), names.index("RightHand"), names.index("LeftHand")
    lf, rf = names.index("LeftToeBase"), names.index("RightToeBase")
    print(f"{src}: {len(data)} 帧 @ {out['fps']}fps，导出 {f0}-{f1}")
    for f in range(0, len(frames), 30):
        print(
            f"  帧{f0 + f:4d} t={f / out['fps']:.2f}s 髋高 {frames[f, hips, 1]:.2f} 右手高 {frames[f, rh, 1]:.2f} 左手高 {frames[f, lh, 1]:.2f}"
            f" 左脚 {frames[f, lf, 1]:.2f} 右脚 {frames[f, rf, 1]:.2f} 髋水平 ({frames[f, hips, 0]:.2f},{frames[f, hips, 2]:.2f})"
        )
    peak = int(np.argmax(np.maximum(frames[:, rh, 1], frames[:, lh, 1])))
    print(f"  手最高点：帧{f0 + peak} t={peak / out['fps']:.2f}s 高度 {max(frames[peak, rh, 1], frames[peak, lh, 1]):.2f}m")


main()
