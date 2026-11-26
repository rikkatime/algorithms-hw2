"""외부 라이브러리 없이 SVG 선 그래프를 그린다 (실험 결과용).

panels: [{"title", "xlabel", "ylabel", "xmax", "ymax", "series": [...]}]
series: {"name", "color", "points": [(x, y), ...], "dashed": bool, "markers": bool}
이론값은 선(점선 가능), 실험값은 점으로 그린다. 점마다 <title>이 있어 마우스를 올리면 값이 보인다.
"""
from xml.sax.saxutils import escape

PANEL_W, PANEL_H = 480, 340
LEFT, RIGHT, TOP, BOTTOM = 56, 16, 40, 48
LEGEND_ROW = 22
TEXT = "#191919"
TEXT2 = "#666666"
GRID = "#e6e6e6"


def _nice_step(span, target=6):
    raw = span / target
    mag = 1
    while mag * 10 <= raw:
        mag *= 10
    while mag > raw:
        mag /= 10
    for m in (1, 2, 2.5, 5, 10):
        if mag * m >= raw:
            return mag * m
    return mag * 10


def _fmt(v):
    return ("%.2f" % v).rstrip("0").rstrip(".")


def _panel(p, ox, oy):
    out = []
    w = PANEL_W - LEFT - RIGHT
    h = PANEL_H - TOP - BOTTOM
    xmax, ymax = p["xmax"], p["ymax"]
    xmin = p.get("xmin", 0)

    def X(x):
        return ox + LEFT + (x - xmin) / (xmax - xmin) * w

    def Y(y):
        return oy + TOP + h - min(y, ymax) / ymax * h

    out.append('<text x="%g" y="%g" font-size="15" font-weight="600" fill="%s">%s</text>'
               % (ox + LEFT, oy + 22, TEXT, escape(p["title"])))
    ys = _nice_step(ymax)
    v = 0.0
    while v <= ymax + 1e-9:
        out.append('<line x1="%g" x2="%g" y1="%g" y2="%g" stroke="%s" stroke-width="1"/>'
                   % (X(xmin), X(xmax), Y(v), Y(v), GRID))
        out.append('<text x="%g" y="%g" font-size="11" fill="%s" text-anchor="end">%s</text>'
                   % (X(xmin) - 6, Y(v) + 4, TEXT2, _fmt(v)))
        v += ys
    xs = p.get("xstep") or _nice_step(xmax - xmin)
    v = xmin
    while v <= xmax + 1e-9:
        out.append('<text x="%g" y="%g" font-size="11" fill="%s" text-anchor="middle">%s</text>'
                   % (X(v), Y(0) + 16, TEXT2, _fmt(v)))
        v += xs
    out.append('<line x1="%g" x2="%g" y1="%g" y2="%g" stroke="%s" stroke-width="1"/>'
               % (X(xmin), X(xmax), Y(0), Y(0), TEXT2))
    out.append('<text x="%g" y="%g" font-size="12" fill="%s" text-anchor="middle">%s</text>'
               % (X((xmin + xmax) / 2), oy + PANEL_H - 10, TEXT2, escape(p["xlabel"])))
    out.append('<text transform="translate(%g %g) rotate(-90)" font-size="12" fill="%s" '
               'text-anchor="middle">%s</text>'
               % (ox + 14, oy + TOP + h / 2, TEXT2, escape(p["ylabel"])))
    clip_id = "clip%d%d" % (ox, oy)
    out.append('<clipPath id="%s"><rect x="%g" y="%g" width="%g" height="%g"/></clipPath>'
               % (clip_id, X(xmin), oy + TOP - 6, w, h + 6))
    for s in p["series"]:
        pts = s["points"]
        if s.get("markers"):
            for x, y in pts:
                if y > ymax:
                    continue
                out.append('<circle cx="%.1f" cy="%.1f" r="4.5" fill="%s" stroke="#ffffff" '
                           'stroke-width="2"><title>%s · α=%s: %.3f</title></circle>'
                           % (X(x), Y(y), s["color"], escape(s["name"]), _fmt(x), y))
        else:
            d = " ".join("%s%.1f %.1f" % ("M" if i == 0 else "L", X(x), Y(y))
                         for i, (x, y) in enumerate(pts))
            dash = ' stroke-dasharray="6 5"' if s.get("dashed") else ""
            out.append('<path d="%s" fill="none" stroke="%s" stroke-width="2"%s '
                       'clip-path="url(#%s)"><title>%s</title></path>'
                       % (d, s["color"], dash, clip_id, escape(s["name"])))
    return out


def _text_width(t):
    return sum(12.5 if ord(c) > 127 else 7.0 for c in t)


def _legend(series, x, y, max_x):
    """범례. 폭을 넘으면 다음 줄로. (svg 조각, 쓴 줄 수)"""
    out = []
    cx, rows = x, 1
    for s in series:
        item_w = 24 + _text_width(s["name"]) + 22
        if cx + item_w > max_x and cx > x:
            cx, y, rows = x, y + LEGEND_ROW, rows + 1
        if s.get("markers"):
            out.append('<circle cx="%g" cy="%g" r="4.5" fill="%s"/>' % (cx + 9, y - 4, s["color"]))
        else:
            dash = ' stroke-dasharray="6 5"' if s.get("dashed") else ""
            out.append('<line x1="%g" x2="%g" y1="%g" y2="%g" stroke="%s" stroke-width="2"%s/>'
                       % (cx, cx + 18, y - 4, y - 4, s["color"], dash))
        out.append('<text x="%g" y="%g" font-size="12" fill="%s">%s</text>'
                   % (cx + 24, y, TEXT, escape(s["name"])))
        cx += item_w
    return out, rows


def write_svg(path, panels, legend_series, title=None):
    width = PANEL_W * len(panels)
    top = 34 if title else 6
    legend, rows = _legend(legend_series, 16, top + 16, width - 10)
    height = top + LEGEND_ROW * rows + PANEL_H + 8
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '
           'font-family="sans-serif">' % (width, height, width, height),
           '<rect width="100%" height="100%" fill="#ffffff"/>']
    if title:
        out.append('<text x="16" y="24" font-size="17" font-weight="700" fill="%s">%s</text>'
                   % (TEXT, escape(title)))
    out += legend
    for i, p in enumerate(panels):
        out += _panel(p, i * PANEL_W, top + LEGEND_ROW * rows)
    out.append("</svg>")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
