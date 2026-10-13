"""写 picks.json：每个标签一组 (素材, 入点秒)。入点取自 sheets/ 接触印样里的镜头起点，略往后让过转场。"""
import json
from pathlib import Path

HERE = Path(__file__).parent

LABEL = {s["name"]: s["work"] for s in json.loads((HERE / "sources.json").read_text())}
CROP = {
    "nami_1991_promo": [0.131, 0, 0.742, 1],
    "aishiatte_op": [0.078, 0, 0.844, 1],
    "disco_nyny": [0.125, 0, 0.75, 1],
    "ski_1987_full": [0.09, 0.04, 0.8, 0.8],
}

P = {
    "tokyo_night": [("tokyo_night_1987", 290.0), ("tokyo_night_1987", 200.0), ("mizugi_1989_full", 353.5), ("tokyo_night_1987", 350.0)],
    "money_taxi": [("bubblego_trailer", 44.5)],
    "shoulder": [("ski_1987_full", 2081.5), ("ski_1987_full", 2060.6)],
    "toast": [("bubblego_trailer", 40.8), ("ski_1987_trailer", 56.5), ("tahosuru_ed", 15.8)],
    "fan": [("disco_nyny", 479.0), ("disco_nyny", 425.0)],
    "office": [("office_80s", 40.0), ("ski_1987_full", 1841.0)],
    "react": [("tahosuru_op", 8.75), ("disco_nyny", 34.9), ("mizugi_1989_full", 5669.2),
              ("nami_1991_promo", 41.75), ("bubblego_trailer", 80.9), ("ski_1987_full", 5742.5)],
    "kaeri": [("ski_1987_full", 5723.8), ("ski_1987_trailer", 50.7)],
    "party": [("disco_nyny", 425.0), ("bubblego_trailer", 55.0), ("tahosuru_ed", 6.7), ("aishiatte_op", 5.8), ("ski_1987_full", 5618.5),
              ("bubblego_trailer", 79.9), ("mizugi_1989_full", 1637.0), ("tahosuru_ed", 11.3), ("ski_1987_trailer", 56.5),
              ("disco_nyny", 367.0), ("ski_1987_full", 5702.3), ("disco_nyny", 185.0), ("mizugi_1989_full", 5701.6), ("bubblego_trailer", 80.9)],
    "ski": [("ski_1987_full", 4018.5), ("ski_1987_trailer", 28.9), ("ski_1987_full", 4043.0)],
    "shopping": [("mizugi_1989_full", 2937.0)],
    "karaoke": [("tahosuru_ed", 33.2)],
    "regain": [("regain_cm", 16.3)],
    "salaryman": [("office_80s", 161.0), ("regain_cm", 134.8)],
    "money_rain": [("bubblego_trailer", 45.8), ("mizugi_1989_full", 198.7)],
    "react_day": [("mizugi_1989_full", 463.8), ("mizugi_1989_full", 4693.7), ("mizugi_1989_full", 5686.0),
                  ("nami_1991_promo", 75.95), ("mizugi_1989_full", 5696.2), ("nami_1991_promo", 71.45)],
    "sunset": [("nami_1991_promo", 84.85), ("regain_cm", 186.9)],
    "pool_party": [("mizugi_1989_full", 5701.6), ("mizugi_1989_full", 5663.3), ("mizugi_1989_full", 4761.5),
                   ("regain_cm", 150.0)],
    "smile": [("ski_1987_full", 601.2), ("tahosuru_ed", 19.4), ("mizugi_1989_full", 5696.2), ("tahosuru_ed", 27.2)],
}
BLURRY = {("disco_nyny", 425.0), ("bubblego_trailer", 55.0)}
P["grid"] = list(dict.fromkeys(
    x for tag in ("smile", "react_day", "toast", "react", "party", "ski", "pool_party", "kaeri", "shoulder",
                  "tokyo_night", "money_taxi", "regain") for x in P[tag] if x not in BLURRY))


def entry(name, t):
    e = {"file": f"raw/{name}.mp4", "in": t, "label": LABEL[name]}
    if name in CROP:
        e["crop"] = CROP[name]
    return e


picks = {tag: [entry(*x) for x in xs] for tag, xs in P.items()}
(HERE / "picks.json").write_text(json.dumps(picks, ensure_ascii=False, indent=1))
print({k: len(v) for k, v in picks.items()})
