#!/usr/bin/env python3
"""SignalSim GUI - four alternative PyQt6 layouts, each with a modern theme.

    pip install PyQt6
    python3 pyqt/signalsim_layouts.py                 # open the layout picker window
    python3 pyqt/signalsim_layouts.py --shots         # write screenshots/pyqt-*.png
    python3 pyqt/signalsim_layouts.py --shots --layout map   # one layout in every theme

Layouts
    dashboard  - sidebar navigation + KPI cards + sky plot + C/N0 chart   (Midnight Indigo)
    mission    - dense "mission control" console: sky, spectrum, table, log (Radar)
    wizard     - step-by-step setup, constellation cards                    (Paper Light)
    map        - trajectory map with floating control cards                 (Nord Frost)

Colours come from ../themes/themes.json and base widget styling from ../themes/signalsim.qss,
so any layout can be combined with any theme (--theme <id>).
"""
import json
import math
import os
import random
import re
import sys
import tempfile

if "--shots" in sys.argv:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_SCALE_FACTOR", "1.5")

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (QBrush, QColor, QFont, QFontDatabase, QImage, QLinearGradient,
                         QPainter, QPainterPath, QPalette, QPen)
from PyQt6.QtWidgets import (QApplication, QButtonGroup, QCheckBox, QComboBox,
                             QDoubleSpinBox, QFormLayout, QFrame, QGridLayout, QHBoxLayout,
                             QHeaderView, QLabel, QLineEdit, QMainWindow, QPlainTextEdit,
                             QProgressBar, QPushButton, QRadioButton, QSlider, QSizePolicy,
                             QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THEME_DIR = os.path.join(ROOT, "themes")
SHOTS = os.path.join(ROOT, "screenshots")
AF = Qt.AlignmentFlag

# ====================================================================== theme engine
UI_FONTS = ["Inter", "Segoe UI Variable Text", "Segoe UI", "SF Pro Text", "Noto Sans", "DejaVu Sans"]
MONO_FONTS = ["JetBrains Mono", "Cascadia Mono", "Consolas", "SF Mono", "DejaVu Sans Mono"]


def first_family(cands):
    have = set(QFontDatabase.families())
    return next((f for f in cands if f in have), cands[-1])


def load_themes():
    with open(os.path.join(THEME_DIR, "themes.json"), encoding="utf-8") as f:
        data = json.load(f)
    return {t["id"]: t for t in data["themes"]}


def _icon(path, color, pts, width):
    img = QImage(32, 32, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor(color), width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    pp = QPainterPath(QPointF(*pts[0]))
    for pt in pts[1:]:
        pp.lineTo(*pt)
    p.drawPath(pp)
    p.end()
    img.save(path, "PNG")


def apply_theme(app, theme):
    c = theme["colors"]
    tok = dict(c)
    d = os.path.join(tempfile.gettempdir(), "signalsim-pyqt-icons")
    os.makedirs(d, exist_ok=True)
    for key, col, pts, w in (("checkIcon", c["accentText"], [(8, 16.5), (13.5, 22), (24, 10.5)], 4.2),
                             ("arrowDown", c["textMuted"], [(9, 12), (16, 19), (23, 12)], 3.6),
                             ("arrowUp", c["textMuted"], [(9, 20), (16, 13), (23, 20)], 3.6),
                             ("arrowDownAccent", c["accent"], [(9, 12), (16, 19), (23, 12)], 3.6)):
        path = os.path.join(d, f"{theme['id']}-{key}.png")
        _icon(path, col, pts, w)
        tok[key] = path.replace(os.sep, "/")
    tok["font"] = first_family(UI_FONTS)
    tok["mono"] = first_family(MONO_FONTS)
    with open(os.path.join(THEME_DIR, "signalsim.qss"), encoding="utf-8") as f:
        qss = re.sub(r"\{\{(\w+)\}\}", lambda m: tok[m.group(1)], f.read())
    qss += EXTRA_QSS.format(**tok)
    pal = QPalette()
    R = QPalette.ColorRole
    for role, key in ((R.Window, "bg"), (R.WindowText, "text"), (R.Base, "surface2"), (R.AlternateBase, "surface"),
                      (R.Text, "text"), (R.Button, "surface2"), (R.ButtonText, "text"), (R.Highlight, "accent"),
                      (R.HighlightedText, "accentText"), (R.PlaceholderText, "textFaint"), (R.Mid, "border")):
        pal.setColor(role, QColor(c[key]))
    app.setPalette(pal)
    app.setStyleSheet(qss)


# Extra rules for the new layouts (single braces are format fields).
EXTRA_QSS = """
QFrame#sidebar {{ background: {header}; border-right: 1px solid {border}; }}
QPushButton#navButton {{
    background: transparent; border: none; border-radius: 10px; color: {textMuted};
    text-align: left; padding: 10px 14px; font-weight: 600;
}}
QPushButton#navButton:hover {{ background: {surface2}; color: {text}; }}
QPushButton#navButton:checked {{ background: {accentSoft}; color: {text}; }}
QLabel#brand {{ font-size: 14pt; font-weight: 800; color: {text}; }}
QLabel#h1 {{ font-size: 18pt; font-weight: 800; color: {text}; }}
QLabel#h2 {{ font-size: 11pt; font-weight: 700; color: {text}; }}
QLabel#muted {{ color: {textMuted}; }}
QLabel#faint {{ color: {textFaint}; font-size: 9pt; }}
QLabel#mono {{ font-family: "{mono}"; color: {textMuted}; }}
QLabel#chip {{
    background: {surface2}; border: 1px solid {border}; border-radius: 10px;
    padding: 3px 10px; color: {textMuted}; font-size: 9pt; font-weight: 600;
}}
QLabel#chip[tone="ok"] {{ color: {ok}; border-color: {ok}; }}
QLabel#chip[tone="warn"] {{ color: {warn}; border-color: {warn}; }}
QLabel#chip[tone="accent"] {{ color: {accentText}; background: {accent}; border-color: {accent}; }}
QFrame#card {{ background: {surface}; border: 1px solid {border}; border-radius: 14px; }}
QFrame#card[floating="true"] {{ border: 1px solid {borderStrong}; }}
QFrame#cardSelected {{ background: {accentSoft}; border: 2px solid {accent}; border-radius: 14px; }}
QFrame#panel {{ background: {surface}; border: 1px solid {border}; border-radius: 6px; }}
QLabel#panelTitle {{
    color: {accent}; font-family: "{mono}"; font-size: 8pt; font-weight: 700; letter-spacing: 2px;
}}
QLabel#bigValue {{ font-family: "{mono}"; font-size: 22pt; font-weight: 700; color: {text}; }}
QLabel#bigValue[tone="ok"] {{ color: {ok}; }}
QLabel#bigValue[tone="warn"] {{ color: {warn}; }}
QLabel#bigValue[tone="info"] {{ color: {info}; }}
QLabel#stepDot {{
    background: {surface2}; color: {textMuted}; border: 1px solid {borderStrong};
    border-radius: 15px; min-width: 30px; max-width: 30px; min-height: 30px; max-height: 30px;
    font-weight: 800; qproperty-alignment: AlignCenter;
}}
QLabel#stepDot[state="done"] {{ background: {accent}; color: {accentText}; border-color: {accent}; }}
QLabel#stepDot[state="active"] {{ background: {accentSoft}; color: {accent}; border: 2px solid {accent}; }}
QLabel#stepLabel {{ color: {textMuted}; font-weight: 600; }}
QLabel#stepLabel[state="active"] {{ color: {text}; font-weight: 800; }}
QFrame#stepLine {{ background: {border}; max-height: 2px; min-height: 2px; }}
QFrame#stepLine[state="done"] {{ background: {accent}; }}
QPushButton#ghost {{ background: transparent; border: 1px solid {borderStrong}; }}
QPushButton#primary {{
    background: {accent}; color: {accentText}; border: none; border-radius: 10px;
    padding: 9px 22px; font-weight: 800;
}}
QPushButton#primary:hover {{ background: {accentHover}; }}
QPushButton#bigStart {{
    background: {accent}; color: {accentText}; border: none; border-radius: 6px;
    font-family: "{mono}"; font-size: 13pt; font-weight: 800; padding: 14px; letter-spacing: 2px;
}}
QPushButton#bigStop {{
    background: transparent; color: {danger}; border: 2px solid {danger}; border-radius: 6px;
    font-family: "{mono}"; font-size: 13pt; font-weight: 800; padding: 12px; letter-spacing: 2px;
}}
QPlainTextEdit#log {{
    background: {bg}; border: none; font-family: "{mono}"; font-size: 8pt; color: {textMuted};
}}
QTableWidget {{ font-family: "{mono}"; font-size: 8pt; }}
"""

# ====================================================================== demo data
RNG = random.Random(7)
SATS = []
for sys_, prefix, n in (("GPS", "G", 9), ("GAL", "E", 7), ("BDS", "C", 7)):
    for i in range(n):
        SATS.append({"sys": sys_, "prn": f"{prefix}{RNG.randint(1, 36):02d}", "az": RNG.uniform(0, 360),
                     "el": RNG.uniform(8, 85), "cn0": RNG.uniform(36, 49), "dop": RNG.uniform(-3800, 3800)})
SATS.sort(key=lambda s: (s["sys"], s["prn"]))


def sys_colors(c):
    return {"GPS": QColor(c["accent"]), "GAL": QColor(c["info"]), "BDS": QColor(c["warn"])}


# ====================================================================== painted widgets
class ThemedPaint(QWidget):
    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.c = theme["colors"]
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def col(self, k, a=255):
        q = QColor(self.c[k])
        q.setAlpha(a)
        return q

    def painter(self):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        return p


class SkyPlot(ThemedPaint):
    """Polar azimuth/elevation plot of the simulated satellites."""

    def __init__(self, theme, labels=True, parent=None):
        super().__init__(theme, parent)
        self.labels = labels
        self.setMinimumSize(260, 260)

    def paintEvent(self, _):
        p = self.painter()
        w, h = self.width(), self.height()
        r = min(w, h) / 2 - 22
        cx, cy = w / 2, h / 2
        grad = QLinearGradient(0, cy - r, 0, cy + r)
        grad.setColorAt(0, self.col("accentSoft", 120))
        grad.setColorAt(1, self.col("surface", 0))
        p.setBrush(QBrush(grad))
        p.setPen(QPen(self.col("borderStrong"), 1))
        p.drawEllipse(QPointF(cx, cy), r, r)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(self.col("border"), 1, Qt.PenStyle.DashLine))
        for el in (30, 60):
            rr = r * (90 - el) / 90
            p.drawEllipse(QPointF(cx, cy), rr, rr)
        for a in range(0, 360, 45):
            t = math.radians(a)
            p.drawLine(QPointF(cx, cy), QPointF(cx + r * math.sin(t), cy - r * math.cos(t)))
        f = QFont(first_family(MONO_FONTS))
        f.setPixelSize(10)
        p.setFont(f)
        p.setPen(self.col("textFaint"))
        for a, n in ((0, "N"), (90, "E"), (180, "S"), (270, "W")):
            t = math.radians(a)
            p.drawText(QRectF(cx + (r + 11) * math.sin(t) - 8, cy - (r + 11) * math.cos(t) - 8, 16, 16),
                       AF.AlignCenter, n)
        sc = sys_colors(self.c)
        for s in SATS:
            rr = r * (90 - s["el"]) / 90
            t = math.radians(s["az"])
            x, y = cx + rr * math.sin(t), cy - rr * math.cos(t)
            col = sc[s["sys"]]
            halo = QColor(col)
            halo.setAlpha(60)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(halo)
            p.drawEllipse(QPointF(x, y), 9, 9)
            p.setBrush(col)
            p.drawEllipse(QPointF(x, y), 4.5, 4.5)
            if self.labels:
                p.setPen(self.col("textMuted"))
                p.drawText(QPointF(x + 8, y - 6), s["prn"])
        p.end()


class Cn0Bars(ThemedPaint):
    """C/N0 bar chart per satellite."""

    def __init__(self, theme, parent=None):
        super().__init__(theme, parent)
        self.setMinimumHeight(180)

    def paintEvent(self, _):
        p = self.painter()
        w, h = self.width(), self.height()
        left, bottom, top = 30, 22, 8
        ph = h - bottom - top
        lo, hi = 30, 52
        f = QFont(first_family(MONO_FONTS))
        f.setPixelSize(9)
        p.setFont(f)
        for v in (30, 40, 50):
            y = top + ph * (1 - (v - lo) / (hi - lo))
            p.setPen(QPen(self.col("border"), 1, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(left, y), QPointF(w, y))
            p.setPen(self.col("textFaint"))
            p.drawText(QRectF(0, y - 7, left - 6, 14), AF.AlignRight | AF.AlignVCenter, str(v))
        n = len(SATS)
        bw = (w - left) / n
        sc = sys_colors(self.c)
        for i, s in enumerate(SATS):
            bh = ph * (s["cn0"] - lo) / (hi - lo)
            x = left + i * bw + bw * 0.18
            rect = QRectF(x, top + ph - bh, bw * 0.64, bh)
            g = QLinearGradient(rect.topLeft(), rect.bottomLeft())
            c1 = QColor(sc[s["sys"]])
            c2 = QColor(sc[s["sys"]])
            c2.setAlpha(70)
            g.setColorAt(0, c1)
            g.setColorAt(1, c2)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(g))
            p.drawRoundedRect(rect, 3, 3)
            p.setPen(self.col("textFaint"))
            p.save()
            p.translate(x + bw * 0.32, h - 2)
            p.rotate(-90)
            p.drawText(QPointF(0, 3), s["prn"])
            p.restore()
        p.end()


class Spectrum(ThemedPaint):
    """Simulated spectrum of the generated band with a waterfall strip."""

    def __init__(self, theme, parent=None):
        super().__init__(theme, parent)
        self.setMinimumHeight(170)
        rng = random.Random(3)
        self.pts = []
        for i in range(400):
            x = i / 399
            v = -98 + rng.gauss(0, 1.4)
            for c0, bw, amp in ((0.5, 0.22, 9), (0.28, 0.08, 5), (0.72, 0.1, 6)):
                v += amp * math.exp(-((x - c0) / bw) ** 4)
            self.pts.append(v)

    def paintEvent(self, _):
        p = self.painter()
        w, h = self.width(), self.height()
        wf = 44
        sh = h - wf - 18
        lo, hi = -104, -80

        def y(v):
            return 4 + (sh - 8) * (1 - (v - lo) / (hi - lo))

        p.setPen(QPen(self.col("border"), 1, Qt.PenStyle.DotLine))
        for gx in range(1, 10):
            p.drawLine(QPointF(w * gx / 10, 0), QPointF(w * gx / 10, sh))
        for gv in (-100, -95, -90, -85):
            p.drawLine(QPointF(0, y(gv)), QPointF(w, y(gv)))
        path = QPainterPath(QPointF(0, sh))
        for i, v in enumerate(self.pts):
            path.lineTo(w * i / (len(self.pts) - 1), y(v))
        path.lineTo(w, sh)
        g = QLinearGradient(0, 0, 0, sh)
        g.setColorAt(0, self.col("accent", 150))
        g.setColorAt(1, self.col("accent", 10))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(g))
        p.drawPath(path)
        line = QPainterPath(QPointF(0, y(self.pts[0])))
        for i, v in enumerate(self.pts):
            line.lineTo(w * i / (len(self.pts) - 1), y(v))
        p.setPen(QPen(self.col("accent"), 1.4))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(line)
        # waterfall
        rng = random.Random(11)
        cols, rows = 120, 11
        cw, rh = w / cols, wf / rows
        for r in range(rows):
            for k in range(cols):
                v = self.pts[int(k / cols * 399)] + rng.gauss(0, 1.2)
                a = max(0.0, min(1.0, (v - lo) / (hi - lo)))
                p.fillRect(QRectF(k * cw, sh + 6 + r * rh, cw + 0.5, rh + 0.5), self.col("accent", int(20 + a * 220)))
        f = QFont(first_family(MONO_FONTS))
        f.setPixelSize(9)
        p.setFont(f)
        p.setPen(self.col("textFaint"))
        for i, lab in enumerate(("1558.6", "1563.3", "1568.3", "1573.2", "1577.9")):
            x0 = min(max(w * i / 4 - 30, 0), w - 60)
            p.drawText(QRectF(x0, h - 13, 60, 12), AF.AlignCenter, lab)
        p.end()


class MapView(ThemedPaint):
    """Stylised map with a trajectory, waypoints and the current receiver position."""

    def __init__(self, theme, parent=None):
        super().__init__(theme, parent)
        self.setMinimumSize(600, 500)

    def paintEvent(self, _):
        p = self.painter()
        w, h = self.width(), self.height()
        p.fillRect(self.rect(), self.col("bg"))
        rng = random.Random(5)
        # blocks / parks
        for _ in range(70):
            x, y = rng.uniform(-40, w), rng.uniform(-40, h)
            bw, bh = rng.uniform(40, 140), rng.uniform(30, 110)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(self.col("surface", 255) if rng.random() > 0.15 else self.col("ok", 35))
            p.drawRoundedRect(QRectF(x, y, bw, bh), 6, 6)
        # river
        river = QPainterPath(QPointF(-10, h * 0.78))
        river.cubicTo(w * 0.3, h * 0.6, w * 0.55, h * 0.95, w + 10, h * 0.7)
        p.setPen(QPen(self.col("info", 70), 26, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(river)
        # streets
        p.setPen(QPen(self.col("surface2"), 7))
        for i in range(1, 9):
            p.drawLine(QPointF(w * i / 9, 0), QPointF(w * i / 9 + 60, h))
        for i in range(1, 7):
            p.drawLine(QPointF(0, h * i / 7), QPointF(w, h * i / 7 - 40))
        p.setPen(QPen(self.col("borderStrong"), 11))
        p.drawLine(QPointF(0, h * 0.42), QPointF(w, h * 0.30))
        # route
        wp = [(0.12, 0.72), (0.25, 0.48), (0.42, 0.40), (0.58, 0.22), (0.76, 0.30), (0.88, 0.55)]
        pts = [QPointF(w * a, h * b) for a, b in wp]
        route = QPainterPath(pts[0])
        for i in range(1, len(pts)):
            m = (pts[i - 1] + pts[i]) / 2
            route.quadTo(pts[i - 1], m)
        route.lineTo(pts[-1])
        p.setPen(QPen(self.col("accent", 70), 14, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawPath(route)
        p.setPen(QPen(self.col("accent"), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawPath(route)
        f = QFont(first_family(UI_FONTS))
        f.setPixelSize(11)
        f.setBold(True)
        p.setFont(f)
        for i, pt in enumerate(pts):
            p.setPen(QPen(self.col("accent"), 3))
            p.setBrush(self.col("surface"))
            p.drawEllipse(pt, 11, 11)
            p.setPen(self.col("text"))
            p.drawText(QRectF(pt.x() - 11, pt.y() - 11, 22, 22), AF.AlignCenter, str(i + 1))
        # current position (between wp 3 and 4)
        cur = route.pointAtPercent(0.58)
        for rad, a in ((34, 30), (22, 60)):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(self.col("warn", a))
            p.drawEllipse(cur, rad, rad)
        p.setBrush(self.col("warn"))
        p.setPen(QPen(self.col("bg"), 3))
        p.drawEllipse(cur, 9, 9)
        p.end()


# ====================================================================== small builders
def lab(text, name=None, **props):
    w = QLabel(text)
    if name:
        w.setObjectName(name)
    for k, v in props.items():
        w.setProperty(k, v)
    return w


def card(name="card", margins=16, spacing=10, **props):
    f = QFrame()
    f.setObjectName(name)
    for k, v in props.items():
        f.setProperty(k, v)
    v = QVBoxLayout(f)
    v.setContentsMargins(margins, margins, margins, margins)
    v.setSpacing(spacing)
    return f, v


def dspin(value, dec, suffix):
    s = QDoubleSpinBox()
    s.setRange(-1e6, 1e6)
    s.setDecimals(dec)
    s.setValue(value)
    s.setSuffix(suffix)
    return s


def check(text, on=False):
    c = QCheckBox(text)
    c.setChecked(on)
    return c


def hbox(*widgets, spacing=8, stretch_last=False):
    h = QHBoxLayout()
    h.setSpacing(spacing)
    for w in widgets:
        if w is None:
            h.addStretch(1)
        elif isinstance(w, QWidget):
            h.addWidget(w)
        else:
            h.addLayout(w)
    return h


def legend(theme):
    sc = sys_colors(theme["colors"])
    h = QHBoxLayout()
    h.setSpacing(14)
    for k, name in (("GPS", "GPS"), ("GAL", "Galileo"), ("BDS", "BeiDou")):
        h.addWidget(lab(f"<span style='color:{sc[k].name()}'>●</span> {name}", "faint"))
    h.addStretch(1)
    return h


# ====================================================================== layout 1: sidebar dashboard
def build_dashboard(theme):
    win = QWidget()
    win.setObjectName("central")
    root = QHBoxLayout(win)
    root.setContentsMargins(0, 0, 0, 0)
    root.setSpacing(0)

    side = QFrame()
    side.setObjectName("sidebar")
    side.setFixedWidth(230)
    sv = QVBoxLayout(side)
    sv.setContentsMargins(16, 20, 16, 16)
    sv.setSpacing(4)
    sv.addWidget(lab("🛰  SignalSim", "brand"))
    sv.addWidget(lab("GNSS signal simulator", "faint"))
    sv.addSpacing(18)
    group = QButtonGroup(side)
    for i, (icon, name) in enumerate((("◉", "Overview"), ("⌖", "Receiver"), ("≋", "Signals"),
                                      ("⇥", "Output / SDR"), ("☰", "Scenarios"), ("⚙", "Settings"))):
        b = QPushButton(f"{icon}   {name}")
        b.setObjectName("navButton")
        b.setCheckable(True)
        b.setChecked(i == 0)
        group.addButton(b)
        sv.addWidget(b)
    sv.addStretch(1)
    dev, dv = card(margins=12, spacing=4)
    dv.addWidget(lab("DEVICE", "tileLabel"))
    dv.addWidget(lab("B206mini", "h2"))
    dv.addWidget(lab("serial 3271A9F · USB 3", "faint"))
    dv.addWidget(lab("● connected", "chip", tone="ok"))
    sv.addWidget(dev)
    root.addWidget(side)

    main = QWidget()
    mv = QVBoxLayout(main)
    mv.setContentsMargins(26, 22, 26, 22)
    mv.setSpacing(16)
    root.addWidget(main, 1)

    top = QHBoxLayout()
    tt = QVBoxLayout()
    tt.setSpacing(2)
    tt.addWidget(lab("Overview", "h1"))
    tt.addWidget(lab("Munich static · L1CA + E1 + B1I · started 12:00:00 UTC", "muted"))
    top.addLayout(tt)
    top.addStretch(1)
    top.addWidget(lab("TEST ONLY", "chip", tone="warn"))
    sb = QPushButton("💾  Save")
    sb.setObjectName("ghost")
    top.addWidget(sb)
    stop = QPushButton("■  STOP RF")
    stop.setObjectName("estopButton")
    top.addWidget(stop)
    mv.addLayout(top)

    kpis = QHBoxLayout()
    kpis.setSpacing(14)
    for title, value, sub, tone, prog in (("Generator speed", "1.42×", "needs ≥ 1.05× for live", "ok", 71),
                                          ("Satellites", "23", "GPS 9 · GAL 7 · BDS 7", "info", None),
                                          ("Signal gaps", "0", "no underruns", "ok", None),
                                          ("Elapsed", "04:12", "of 10:00", None, 42)):
        k, kv = card(margins=16, spacing=4)
        kv.addWidget(lab(title.upper(), "tileLabel"))
        kv.addWidget(lab(value, "bigValue", tone=tone or ""))
        kv.addWidget(lab(sub, "faint"))
        if prog is not None:
            pb = QProgressBar()
            pb.setValue(prog)
            pb.setTextVisible(False)
            pb.setFixedHeight(6)
            kv.addWidget(pb)
        kpis.addWidget(k)
    mv.addLayout(kpis)

    mid = QHBoxLayout()
    mid.setSpacing(14)
    sky, skv = card()
    skv.addLayout(hbox(lab("Sky view", "h2"), None, lab("mask 5°", "chip")))
    skv.addWidget(SkyPlot(theme), 1)
    skv.addLayout(legend(theme))
    mid.addWidget(sky, 4)
    cn, cnv = card()
    cnv.addLayout(hbox(lab("Signal strength  (C/N0, dB-Hz)", "h2"), None, lab("45.0 target", "chip")))
    cnv.addWidget(Cn0Bars(theme), 1)
    cnv.addLayout(legend(theme))
    mid.addWidget(cn, 6)
    mv.addLayout(mid, 1)

    quick, qv = card(margins=14)
    row = QHBoxLayout()
    row.setSpacing(18)
    for name, on in (("GPS L1CA", True), ("Galileo E1", True), ("BeiDou B1I", True), ("GLONASS G1", False), ("GPS L5", False)):
        row.addWidget(check(name, on))
    row.addStretch(1)
    row.addWidget(lab("1568.26 MHz · 19.35 MS/s", "mono"))
    qv.addLayout(row)
    mv.addWidget(quick)

    bottom = QHBoxLayout()
    status = lab(f"<span style='color:{theme['colors']['ok']}'>●</span>&nbsp; Streaming to Simulated SDR · "
                 "ephemeris BRDC00WRD (day 305) · 4 threads", "statusLine")
    bottom.addWidget(status, 1)
    start = QPushButton("▶  Start")
    start.setObjectName("startButton")
    start.setMinimumWidth(150)
    bottom.addWidget(start)
    mv.addLayout(bottom)
    return win


# ====================================================================== layout 2: mission control
def panel(title):
    f = QFrame()
    f.setObjectName("panel")
    v = QVBoxLayout(f)
    v.setContentsMargins(12, 10, 12, 12)
    v.setSpacing(8)
    v.addWidget(lab(f"▍{title}", "panelTitle"))
    return f, v


def build_mission(theme):
    c = theme["colors"]
    win = QWidget()
    win.setObjectName("central")
    root = QVBoxLayout(win)
    root.setContentsMargins(12, 10, 12, 12)
    root.setSpacing(10)

    bar = QHBoxLayout()
    bar.addWidget(lab("SIGNALSIM // MISSION CONTROL", "panelTitle"))
    bar.addStretch(1)
    for t, tone in (("UTC 2026-11-01 12:04:12", ""), ("EPH BRDC 305 ✓", "ok"), ("B206mini ✓", "ok"),
                    ("RF: TEST ONLY", "warn")):
        bar.addWidget(lab(t, "chip", tone=tone))
    root.addLayout(bar)

    grid = QGridLayout()
    grid.setSpacing(10)
    root.addLayout(grid, 1)

    sky, sv = panel("SKY // 23 SV TRACKED")
    sv.addWidget(SkyPlot(theme), 1)
    sv.addLayout(legend(theme))
    grid.addWidget(sky, 0, 0, 2, 1)

    spec, spv = panel("SPECTRUM // 1568.26 MHz ± 9.7 MHz")
    spv.addWidget(Spectrum(theme), 1)
    grid.addWidget(spec, 0, 1)

    tab, tv = panel("CHANNELS")
    t = QTableWidget(len(SATS), 6)
    t.setHorizontalHeaderLabels(["SV", "SYS", "AZ°", "EL°", "C/N0", "DOPPLER Hz"])
    t.verticalHeader().setVisible(False)
    t.setShowGrid(False)
    t.setAlternatingRowColors(True)
    t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    t.verticalHeader().setDefaultSectionSize(22)
    for r, s in enumerate(sorted(SATS, key=lambda s: -s["el"])):
        vals = [s["prn"], s["sys"], f"{s['az']:.0f}", f"{s['el']:.0f}", f"{s['cn0']:.1f}", f"{s['dop']:+.0f}"]
        for k, v in enumerate(vals):
            it = QTableWidgetItem(v)
            it.setTextAlignment(AF.AlignCenter)
            if k == 4:
                it.setForeground(QColor(c["ok"] if s["cn0"] > 42 else c["warn"]))
            t.setItem(r, k, it)
    tv.addWidget(t)
    grid.addWidget(tab, 1, 1)

    right = QVBoxLayout()
    right.setSpacing(10)
    for title, value, tone, sub in (("GEN SPEED", "1.42×", "ok", "≥1.05× REQUIRED"),
                                    ("BUFFER", "64%", "warn", "TARGET 50–90%"),
                                    ("GAPS", "0", "ok", "SINCE START")):
        f, v = panel(title)
        v.addWidget(lab(value, "bigValue", tone=tone))
        v.addWidget(lab(sub, "faint"))
        right.addWidget(f)
    ctl, cv = panel("TX CONTROL")
    sl = QSlider(Qt.Orientation.Horizontal)
    sl.setRange(0, 89)
    cv.addLayout(hbox(lab("GAIN", "faint"), sl, lab("0 dB", "mono")))
    cv.addWidget(check("TEST ONLY", True))
    cv.addWidget(check("SHIELDED SETUP OK", False))
    right.addWidget(ctl)
    right.addStretch(1)
    go = QPushButton("▶ ENGAGE")
    go.setObjectName("bigStart")
    right.addWidget(go)
    st = QPushButton("■ STOP RF")
    st.setObjectName("bigStop")
    right.addWidget(st)
    rw = QWidget()
    rw.setLayout(right)
    rw.setFixedWidth(250)
    grid.addWidget(rw, 0, 2, 2, 1)
    grid.setColumnStretch(0, 5)
    grid.setColumnStretch(1, 6)
    grid.setRowStretch(0, 4)
    grid.setRowStretch(1, 5)

    log, lv = panel("EVENT LOG")
    txt = QPlainTextEdit()
    txt.setObjectName("log")
    txt.setReadOnly(True)
    txt.setPlainText("12:00:00.000  scenario loaded  static 48.137154N 11.576124E 520 m\n"
                     "12:00:00.412  ephemeris BRDC00WRD_S_20263050000_01D_MN.rnx  GPS 31 · GAL 24 · BDS 44\n"
                     "12:00:01.003  band auto → 1568.26 MHz / 19.35 MS/s (L1CA E1 B1I)\n"
                     "12:00:01.210  sdr B206mini 3271A9F · master clock 38.70 MHz · TX/RX\n"
                     "12:00:01.355  TEST ONLY — no RF output · streaming to simulated sink\n"
                     "12:04:12.000  speed 1.42× · buffer 64 % · gaps 0")
    txt.setFixedHeight(112)
    lv.addWidget(txt)
    root.addWidget(log)
    return win


# ====================================================================== layout 3: wizard
def build_wizard(theme):
    win = QWidget()
    win.setObjectName("central")
    outer = QVBoxLayout(win)
    outer.setContentsMargins(0, 0, 0, 0)
    head = QFrame()
    head.setObjectName("headerBar")
    hv = QHBoxLayout(head)
    hv.setContentsMargins(28, 14, 28, 14)
    hv.addWidget(lab("🛰  New simulation", "brand"))
    hv.addStretch(1)
    hv.addWidget(lab("Draft · autosaved", "faint"))
    outer.addWidget(head)

    body = QVBoxLayout()
    body.setContentsMargins(60, 26, 60, 26)
    body.setSpacing(22)
    outer.addLayout(body, 1)

    steps = QHBoxLayout()
    steps.setSpacing(10)
    names = ["Location", "Time & ephemeris", "Signals", "Output", "Review"]
    for i, n in enumerate(names):
        state = "done" if i < 2 else "active" if i == 2 else ""
        col = QHBoxLayout()
        col.setSpacing(8)
        col.addWidget(lab("✓" if state == "done" else str(i + 1), "stepDot", state=state))
        col.addWidget(lab(n, "stepLabel", state=state))
        steps.addLayout(col)
        if i < len(names) - 1:
            line = QFrame()
            line.setObjectName("stepLine")
            line.setProperty("state", "done" if i < 2 else "")
            line.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            steps.addWidget(line, 1)
    body.addLayout(steps)

    body.addWidget(lab("Which signals should the simulator generate?", "h1"))
    body.addWidget(lab("Pick one or more constellations. Signals that fit into one SDR band are combined "
                       "automatically; the centre frequency and sample rate follow your choice.", "muted"))

    cards = QGridLayout()
    cards.setSpacing(16)
    data = [("GPS", "USA · 31 satellites", [("L1CA", True), ("L1C", False), ("L2C", False), ("L5", False)], True),
            ("Galileo", "EU · 24 satellites", [("E1", True), ("E5a", False), ("E5b", False)], True),
            ("BeiDou", "China · 44 satellites", [("B1I", True), ("B1C", False), ("B2a", False)], True),
            ("GLONASS", "Russia · 22 satellites", [("G1", False), ("G2", False)], False)]
    for i, (name, sub, sigs, sel) in enumerate(data):
        f, v = card("cardSelected" if sel else "card", margins=18, spacing=8)
        v.addLayout(hbox(lab(name, "h2"), None, lab("✓ selected" if sel else "add", "chip",
                                                         tone="accent" if sel else "")))
        v.addWidget(lab(sub, "faint"))
        v.addSpacing(4)
        for s, on in sigs:
            v.addWidget(check(s, on))
        v.addStretch(1)
        cards.addWidget(f, 0, i)
    body.addLayout(cards)
    body.addStretch(1)

    sumc, sv = card(margins=16)
    row = QHBoxLayout()
    row.setSpacing(28)
    for k, v in (("Band", "1559.05 – 1577.47 MHz"), ("Centre", "1568.26 MHz"), ("Sample rate", "19.35 MS/s"),
                 ("Signals", "23 in view"), ("Est. speed", "1.4× real time")):
        col = QVBoxLayout()
        col.setSpacing(2)
        col.addWidget(lab(k.upper(), "tileLabel"))
        col.addWidget(lab(v, "h2"))
        row.addLayout(col)
    row.addStretch(1)
    row.addWidget(check("Auto centre / rate", True))
    sv.addLayout(row)
    body.addWidget(sumc)

    nav = QHBoxLayout()
    back = QPushButton("←  Back")
    back.setObjectName("ghost")
    nav.addWidget(back)
    nav.addStretch(1)
    nav.addWidget(lab("Step 3 of 5", "faint"))
    nav.addSpacing(12)
    nx = QPushButton("Continue  →")
    nx.setObjectName("primary")
    nav.addWidget(nx)
    body.addLayout(nav)
    return win


# ====================================================================== layout 4: map
def build_map(theme):
    win = QWidget()
    win.setObjectName("central")
    grid = QGridLayout(win)
    grid.setContentsMargins(0, 0, 0, 0)
    grid.addWidget(MapView(theme), 0, 0)

    over = QWidget()
    over.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    ov = QHBoxLayout(over)
    ov.setContentsMargins(18, 18, 18, 18)
    ov.setSpacing(18)
    grid.addWidget(over, 0, 0)

    left = QVBoxLayout()
    left.setSpacing(14)
    route, rv = card(margins=16, floating="true")
    route.setFixedWidth(330)
    rv.addLayout(hbox(lab("Trajectory", "h2"), None, lab("6 waypoints", "chip")))
    for i, (name, coord) in enumerate((("Start · Marienplatz", "48.1372, 11.5755"), ("Isartor", "48.1350, 11.5822"),
                                       ("Deutsches Museum", "48.1299, 11.5834"), ("Gasteig", "48.1316, 11.5926"),
                                       ("Max-Weber-Platz", "48.1357, 11.5985"), ("End · Ostbahnhof", "48.1272, 11.6047"))):
        r = QHBoxLayout()
        r.addWidget(lab(f"{i + 1}", "stepDot", state="done" if i < 3 else "active" if i == 3 else ""))
        col = QVBoxLayout()
        col.setSpacing(0)
        col.addWidget(lab(name))
        col.addWidget(lab(coord, "mono"))
        r.addLayout(col, 1)
        rv.addLayout(r)
    form = QFormLayout()
    form.setVerticalSpacing(8)
    form.addRow("Speed", dspin(36.0, 1, " km/h"))
    form.addRow("Altitude", dspin(520.0, 1, " m"))
    rv.addLayout(form)
    rv.addLayout(hbox(QPushButton("+ Add point"), QPushButton("Import KML"), None))
    left.addWidget(route)
    left.addStretch(1)
    ov.addLayout(left)
    ov.addStretch(1)

    right = QVBoxLayout()
    right.setSpacing(14)
    st, stv = card(margins=16, floating="true")
    st.setFixedWidth(300)
    stv.addLayout(hbox(lab("Live", "h2"), None, lab("● running", "chip", tone="ok")))
    g = QGridLayout()
    g.setVerticalSpacing(2)
    for i, (k, v, tone) in enumerate((("SPEED", "1.42×", "ok"), ("SATS", "23", "info"),
                                      ("GAPS", "0", "ok"), ("ELAPSED", "04:12", ""))):
        cell = QVBoxLayout()
        cell.setSpacing(0)
        cell.addWidget(lab(k, "tileLabel"))
        cell.addWidget(lab(v, "bigValue", tone=tone))
        g.addLayout(cell, i // 2, i % 2)
    stv.addLayout(g)
    pb = QProgressBar()
    pb.setValue(58)
    pb.setFormat("route 58 %")
    stv.addWidget(pb)
    right.addWidget(st)

    sky, skv = card(margins=12, floating="true")
    sky.setFixedWidth(300)
    skv.addWidget(lab("Sky", "h2"))
    sp = SkyPlot(theme, labels=False)
    sp.setMinimumSize(250, 230)
    skv.addWidget(sp)
    right.addWidget(sky)
    right.addStretch(1)
    ctl, cv = card(margins=12, floating="true")
    ctl.setFixedWidth(300)
    cv.addWidget(check("Test only (no RF)", True))
    cv.addLayout(hbox(lab("TX gain", "faint"), QSlider(Qt.Orientation.Horizontal), lab("0 dB", "mono")))
    b1 = QPushButton("▶  Start")
    b1.setObjectName("startButton")
    b2 = QPushButton("■  STOP RF")
    b2.setObjectName("estopButton")
    cv.addLayout(hbox(b1, b2))
    right.addWidget(ctl)
    ov.addLayout(right)
    return win


# ====================================================================== app
# ====================================================================== extra painted widgets
class Gauge(ThemedPaint):
    """Circular arc gauge (270°) with value text."""

    def __init__(self, theme, value, lo, hi, text, label, tone="accent", ticks=None, parent=None):
        super().__init__(theme, parent)
        self.v, self.lo, self.hi, self.text, self.label, self.tone = value, lo, hi, text, label, tone
        self.ticks = ticks or []
        self.setMinimumSize(170, 170)

    def paintEvent(self, _):
        p = self.painter()
        w, h = self.width(), self.height()
        r = min(w, h) / 2 - 14
        rect = QRectF(w / 2 - r, h / 2 - r, 2 * r, 2 * r)
        pen = QPen(self.col("surface2"), 12, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawArc(rect, 225 * 16, -270 * 16)
        frac = max(0.0, min(1.0, (self.v - self.lo) / (self.hi - self.lo)))
        g = QPen(self.col(self.tone), 12, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(g)
        p.drawArc(rect, 225 * 16, int(-270 * 16 * frac))
        for t, key in self.ticks:            # threshold markers
            a = math.radians(225 - 270 * (t - self.lo) / (self.hi - self.lo))
            p.setPen(QPen(self.col(key), 3))
            p.drawLine(QPointF(w / 2 + (r - 12) * math.cos(a), h / 2 - (r - 12) * math.sin(a)),
                       QPointF(w / 2 + (r + 8) * math.cos(a), h / 2 - (r + 8) * math.sin(a)))
        f = QFont(first_family(MONO_FONTS))
        f.setPixelSize(int(r * 0.36))
        f.setBold(True)
        p.setFont(f)
        p.setPen(self.col("text"))
        p.drawText(QRectF(0, h / 2 - r * 0.32, w, r * 0.5), AF.AlignCenter, self.text)
        f2 = QFont(first_family(UI_FONTS))
        f2.setPixelSize(max(10, int(r * 0.13)))
        f2.setBold(True)
        p.setFont(f2)
        p.setPen(self.col("textMuted"))
        p.drawText(QRectF(0, h / 2 + r * 0.22, w, r * 0.3), AF.AlignCenter, self.label.upper())
        p.end()


class Cn0Timeline(ThemedPaint):
    """C/N0 of a few satellites over the run, with a playhead."""

    def __init__(self, theme, parent=None):
        super().__init__(theme, parent)
        self.setMinimumHeight(220)

    def paintEvent(self, _):
        p = self.painter()
        w, h = self.width(), self.height()
        left, bottom = 34, 20
        ph, pw = h - bottom - 8, w - left - 8
        lo, hi = 30, 52
        f = QFont(first_family(MONO_FONTS))
        f.setPixelSize(9)
        p.setFont(f)
        for v in (30, 35, 40, 45, 50):
            y = 8 + ph * (1 - (v - lo) / (hi - lo))
            p.setPen(QPen(self.col("border"), 1, Qt.PenStyle.DotLine))
            p.drawLine(QPointF(left, y), QPointF(w - 8, y))
            p.setPen(self.col("textFaint"))
            p.drawText(QRectF(0, y - 7, left - 6, 14), AF.AlignRight | AF.AlignVCenter, str(v))
        for m in range(0, 11, 2):
            x = left + pw * m / 10
            p.drawText(QRectF(min(x - 20, w - 44), h - 16, 40, 14), AF.AlignCenter, f"{m:02d}:00")
        sc = sys_colors(self.c)
        rng = random.Random(9)
        for s in SATS[::3]:
            base = s["cn0"]
            path = QPainterPath()
            for i in range(121):
                t = i / 120
                v = base + 1.6 * math.sin(t * 6 + base) + rng.gauss(0, 0.35)
                if s["prn"] == SATS[6]["prn"] and 0.55 < t < 0.63:
                    v -= 14          # simulated outage (e.g. tunnel)
                pt = QPointF(left + pw * t, 8 + ph * (1 - (v - lo) / (hi - lo)))
                path.moveTo(pt) if i == 0 else path.lineTo(pt)
            col = QColor(sc[s["sys"]])
            col.setAlpha(210)
            p.setPen(QPen(col, 1.6))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)
        x = left + pw * 0.42
        p.setPen(QPen(self.col("warn"), 2))
        p.drawLine(QPointF(x, 4), QPointF(x, 8 + ph))
        p.setBrush(self.col("warn"))
        p.drawEllipse(QPointF(x, 6), 4, 4)
        p.end()


class VisibilityTimeline(ThemedPaint):
    """Per-satellite visibility bars over 24 h, event markers and a playhead."""

    def __init__(self, theme, parent=None):
        super().__init__(theme, parent)
        self.setMinimumHeight(420)

    def paintEvent(self, _):
        p = self.painter()
        w, h = self.width(), self.height()
        left, top = 70, 28
        rows = SATS[:18]
        rh = (h - top - 10) / len(rows)
        pw = w - left - 10
        f = QFont(first_family(MONO_FONTS))
        f.setPixelSize(10)
        p.setFont(f)
        for hr in range(0, 25, 3):
            x = left + pw * hr / 24
            p.setPen(QPen(self.col("border"), 1, Qt.PenStyle.DotLine))
            p.drawLine(QPointF(x, top - 4), QPointF(x, h - 10))
            p.setPen(self.col("textFaint"))
            p.drawText(QRectF(min(x - 22, w - 46), 4, 44, 16), AF.AlignCenter, f"{hr:02d}:00")
        sc = sys_colors(self.c)
        rng = random.Random(21)
        for i, s in enumerate(rows):
            y = top + i * rh
            if i % 2 == 0:
                p.fillRect(QRectF(0, y, w, rh), self.col("surface2", 90))
            p.setPen(self.col("textMuted"))
            p.drawText(QRectF(8, y, left - 14, rh), AF.AlignLeft | AF.AlignVCenter, s["prn"])
            col = QColor(sc[s["sys"]])
            start = rng.uniform(-4, 10)
            while start < 24:
                dur = rng.uniform(3.5, 7)
                a, b = max(start, 0), min(start + dur, 24)
                if b > a:
                    rect = QRectF(left + pw * a / 24, y + rh * 0.22, pw * (b - a) / 24, rh * 0.56)
                    g = QLinearGradient(rect.topLeft(), rect.topRight())
                    c1, c2 = QColor(col), QColor(col)
                    c1.setAlpha(90)
                    c2.setAlpha(230)
                    g.setColorAt(0, c1)
                    g.setColorAt(0.5, c2)
                    g.setColorAt(1, c1)
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(QBrush(g))
                    p.drawRoundedRect(rect, rh * 0.28, rh * 0.28)
                start += dur + rng.uniform(4, 8)
        # playhead
        x = left + pw * 12.07 / 24
        p.setPen(QPen(self.col("accent"), 2))
        p.drawLine(QPointF(x, top - 6), QPointF(x, h - 10))
        p.setBrush(self.col("accent"))
        p.setPen(Qt.PenStyle.NoPen)
        tri = QPainterPath(QPointF(x - 7, top - 12))
        tri.lineTo(x + 7, top - 12)
        tri.lineTo(x, top - 3)
        tri.closeSubpath()
        p.drawPath(tri)
        p.end()


class EventLane(ThemedPaint):
    """Keyframe lane for scenario events."""
    EVENTS = [(0.0, "Start", "ok"), (3.5, "C/N0 −6 dB", "warn"), (7.2, "E12 outage", "err"),
              (12.07, "now", "accent"), (16.0, "Route leg 2", "info"), (21.5, "Stop", "textMuted")]

    def __init__(self, theme, parent=None):
        super().__init__(theme, parent)
        self.setFixedHeight(64)

    def paintEvent(self, _):
        p = self.painter()
        w, h = self.width(), self.height()
        left, pw = 70, w - 80
        p.setPen(QPen(self.col("borderStrong"), 2))
        p.drawLine(QPointF(left, h / 2), QPointF(w - 10, h / 2))
        f = QFont(first_family(UI_FONTS))
        f.setPixelSize(11)
        f.setBold(True)
        p.setFont(f)
        p.setPen(self.col("textMuted"))
        p.drawText(QRectF(8, 0, left - 10, h), AF.AlignLeft | AF.AlignVCenter, "EVENTS")
        for t, name, key in self.EVENTS:
            if name == "now":
                continue
            x = left + pw * t / 24
            d = QPainterPath(QPointF(x, h / 2 - 8))
            d.lineTo(x + 8, h / 2)
            d.lineTo(x, h / 2 + 8)
            d.lineTo(x - 8, h / 2)
            d.closeSubpath()
            p.setPen(QPen(self.col("bg"), 2))
            p.setBrush(self.col(key))
            p.drawPath(d)
            p.setPen(self.col("text"))
            p.drawText(QRectF(x - 60, 2, 120, 16), AF.AlignCenter, name)
        p.end()


# ====================================================================== layout 5: studio (IDE style)
def build_studio(theme):
    from PyQt6.QtWidgets import QTabWidget, QTreeWidget, QTreeWidgetItem
    c = theme["colors"]
    win = QWidget()
    win.setObjectName("central")
    root = QVBoxLayout(win)
    root.setContentsMargins(0, 0, 0, 0)
    root.setSpacing(0)

    tb = QFrame()
    tb.setObjectName("headerBar")
    th = QHBoxLayout(tb)
    th.setContentsMargins(14, 8, 14, 8)
    th.setSpacing(8)
    th.addWidget(lab("🛰  SignalSim Studio", "h2"))
    th.addSpacing(18)
    for t in ("📂 Open", "💾 Save", "⤓ Ephemeris"):
        b = QPushButton(t)
        b.setObjectName("ghost")
        th.addWidget(b)
    th.addStretch(1)
    th.addWidget(lab("munich_route.json — modified", "faint"))
    th.addSpacing(12)
    go = QPushButton("▶  Run")
    go.setObjectName("primary")
    th.addWidget(go)
    st = QPushButton("■  STOP RF")
    st.setObjectName("estopButton")
    th.addWidget(st)
    root.addWidget(tb)

    body = QHBoxLayout()
    body.setContentsMargins(10, 10, 10, 10)
    body.setSpacing(10)
    root.addLayout(body, 1)

    # explorer
    ex, exv = card(margins=10, spacing=6)
    ex.setFixedWidth(250)
    exv.addWidget(lab("EXPLORER", "tileLabel"))
    tree = QTreeWidget()
    tree.setHeaderHidden(True)
    tree.setIndentation(14)
    for top, kids in (("Scenarios", ["munich_static.json", "munich_route.json ●", "e5a_b2a_test.json", "l1_only.json"]),
                      ("Ephemeris", ["BRDC00WRD_S_2026305", "BRD400DLR_S_2026305", "BRDC00IGS_R_2021170"]),
                      ("Routes", ["ostbahnhof.kml", "airport_loop.kml"]),
                      ("Devices", ["B206mini · 3271A9F", "Simulated SDR"])):
        it = QTreeWidgetItem([top])
        for k in kids:
            it.addChild(QTreeWidgetItem([k]))
        tree.addTopLevelItem(it)
        it.setExpanded(top != "Routes")
    tree.setCurrentItem(tree.topLevelItem(0).child(1))
    exv.addWidget(tree, 1)
    body.addWidget(ex)

    # center
    center = QVBoxLayout()
    center.setSpacing(10)
    tabs = QTabWidget()
    tl = QWidget()
    tlv = QVBoxLayout(tl)
    tlv.setContentsMargins(4, 12, 4, 4)
    tlv.addLayout(hbox(lab("C/N0 over time", "h2"), None, lab("playhead 04:12", "chip", tone="warn")))
    tlv.addWidget(Cn0Timeline(theme), 1)
    tlv.addLayout(legend(theme))
    tabs.addTab(tl, "Timeline")
    tabs.addTab(QWidget(), "Spectrum")
    tabs.addTab(QWidget(), "Sky")
    tabs.addTab(QWidget(), "Log")
    tc, tcv = card(margins=12)
    tcv.addWidget(tabs)
    center.addWidget(tc, 3)
    lower = QHBoxLayout()
    lower.setSpacing(10)
    sp, spv = card(margins=12)
    spv.addWidget(lab("Spectrum", "h2"))
    spv.addWidget(Spectrum(theme), 1)
    lower.addWidget(sp, 3)
    kp, kpv = card(margins=14, spacing=6)
    for k, v, tone in (("GEN SPEED", "1.42×", "ok"), ("BUFFER", "64 %", "warn"), ("GAPS", "0", "ok")):
        kpv.addWidget(lab(k, "tileLabel"))
        kpv.addWidget(lab(v, "bigValue", tone=tone))
    lower.addWidget(kp, 1)
    center.addLayout(lower, 2)
    body.addLayout(center, 1)

    # inspector
    ins, iv = card(margins=14, spacing=8)
    ins.setFixedWidth(300)
    iv.addWidget(lab("INSPECTOR", "tileLabel"))
    for section, rows in (("Receiver", [("Mode", "Trajectory"), ("Speed", "36.0 km/h"), ("Altitude", "520.0 m")]),
                          ("Simulation", [("Start", "2026-11-01 12:00"), ("C/N0", "45.0 dB-Hz"), ("Mask", "5°")]),
                          ("Band", [("Centre", "1568.26 MHz"), ("Rate", "19.35 MS/s"), ("Signals", "L1CA · E1 · B1I")]),
                          ("Output", [("Device", "B206mini"), ("Port", "TX/RX"), ("Gain", "0 dB")])):
        iv.addWidget(lab(f"▾  {section}", "h2"))
        g = QFormLayout()
        g.setVerticalSpacing(4)
        for k, v in rows:
            g.addRow(lab(k, "muted"), lab(v, "mono"))
        iv.addLayout(g)
    iv.addWidget(check("Test only (no RF)", True))
    iv.addStretch(1)
    body.addWidget(ins)

    sb = QFrame()
    sb.setObjectName("headerBar")
    sbl = QHBoxLayout(sb)
    sbl.setContentsMargins(14, 5, 14, 5)
    sbl.addWidget(lab(f"<span style='color:{c['ok']}'>●</span> running · Simulated SDR", "faint"))
    sbl.addStretch(1)
    sbl.addWidget(lab("4 threads · CPU 63 % · 1568.26 MHz · 19.35 MS/s · UTC 12:04:12", "faint"))
    root.addWidget(sb)
    return win


# ====================================================================== layout 6: compact panel
def build_compact(theme):
    win = QWidget()
    win.setObjectName("central")
    v = QVBoxLayout(win)
    v.setContentsMargins(20, 18, 20, 18)
    v.setSpacing(14)
    v.addLayout(hbox(lab("🛰  SignalSim", "brand"), None, lab("● B206mini", "chip", tone="ok")))

    g = Gauge(theme, 1.42, 0, 2, "1.42×", "generator speed", "accent", ticks=[(1.05, "warn")])
    g.setMinimumSize(250, 250)
    v.addWidget(g)
    row = QHBoxLayout()
    for k, val, tone in (("SATS", "23", "info"), ("GAPS", "0", "ok"), ("TIME", "04:12", "")):
        cc, cv = card(margins=10, spacing=0)
        cv.addWidget(lab(k, "tileLabel"), 0, AF.AlignHCenter)
        bv = lab(val, "bigValue", tone=tone)
        cv.addWidget(bv, 0, AF.AlignHCenter)
        row.addWidget(cc)
    v.addLayout(row)

    seg = QHBoxLayout()
    seg.setSpacing(0)
    grp = QButtonGroup(win)
    for i, t in enumerate(("Static", "Trajectory", "File")):
        b = QPushButton(t)
        b.setObjectName("navButton")
        b.setCheckable(True)
        b.setChecked(i == 0)
        grp.addButton(b)
        seg.addWidget(b)
    sc, sv = card(margins=6, spacing=0)
    sv.addLayout(seg)
    v.addWidget(sc)

    f = QFormLayout()
    f.setVerticalSpacing(8)
    f.addRow("Position", QLineEdit("48.137154, 11.576124"))
    f.addRow("Altitude", dspin(520.0, 1, " m"))
    f.addRow("Duration", dspin(600, 0, " s"))
    v.addLayout(f)

    v.addWidget(lab("SIGNALS", "tileLabel"))
    chips = QGridLayout()
    chips.setSpacing(6)
    for i, (t, on) in enumerate((("L1CA", 1), ("E1", 1), ("B1I", 1), ("G1", 0), ("L5", 0), ("E5a", 0), ("B2a", 0), ("L1C", 0))):
        chips.addWidget(lab(("✓ " if on else "") + t, "chip", tone="accent" if on else ""), i // 4, i % 4)
    v.addLayout(chips)
    v.addWidget(lab("1568.26 MHz · 19.35 MS/s · auto", "mono"))
    v.addWidget(check("Test only (no RF output)", True))
    v.addStretch(1)
    go = QPushButton("▶  Start simulation")
    go.setObjectName("startButton")
    v.addWidget(go)
    st = QPushButton("■  STOP RF")
    st.setObjectName("estopButton")
    v.addWidget(st)
    return win


# ====================================================================== layout 7: instrument panel
def build_instruments(theme):
    c = theme["colors"]
    win = QWidget()
    win.setObjectName("central")
    root = QHBoxLayout(win)
    root.setContentsMargins(18, 16, 18, 16)
    root.setSpacing(16)

    main = QVBoxLayout()
    main.setSpacing(14)
    main.addLayout(hbox(lab("Instrument panel", "h1"), None, lab("UTC 12:04:12", "chip"),
                        lab("RF: TEST ONLY", "chip", tone="warn")))
    gauges = QHBoxLayout()
    gauges.setSpacing(14)
    for val, lo, hi, txt, label, tone, ticks in ((1.42, 0, 2, "1.42×", "gen speed", "ok", [(1.05, "warn")]),
                                                 (64, 0, 100, "64%", "buffer", "warn", [(50, "ok"), (90, "ok")]),
                                                 (43.1, 30, 52, "43.1", "avg C/N0", "info", [(45, "accent")]),
                                                 (0, 0, 89, "0 dB", "tx gain", "accent", []),
                                                 (63, 0, 100, "63%", "cpu", "accent", [])):
        gc, gv = card(margins=8)
        gv.addWidget(Gauge(theme, val, lo, hi, txt, label, tone, ticks))
        gauges.addWidget(gc)
    main.addLayout(gauges)

    main.addLayout(hbox(lab("Satellites in view", "h2"), None, legend(theme)))
    grid = QGridLayout()
    grid.setSpacing(10)
    sc = sys_colors(c)
    for i, s in enumerate(sorted(SATS, key=lambda s: -s["cn0"])):
        cc, cv = card(margins=10, spacing=3)
        col = sc[s["sys"]].name()
        cv.addLayout(hbox(lab(f"<span style='color:{col}'>●</span> <b>{s['prn']}</b>"), None,
                          lab(f"{s['cn0']:.1f}", "mono")))
        pb = QProgressBar()
        pb.setRange(30, 52)
        pb.setValue(int(s["cn0"]))
        pb.setTextVisible(False)
        pb.setFixedHeight(6)
        pb.setStyleSheet(f"QProgressBar::chunk {{ background: {col}; border-radius: 3px; }}")
        cv.addWidget(pb)
        cv.addWidget(lab(f"az {s['az']:.0f}° · el {s['el']:.0f}°", "faint"))
        grid.addWidget(cc, i // 5, i % 5)
    main.addLayout(grid)
    main.addStretch(1)
    root.addLayout(main, 1)

    side, sv = card(margins=16, spacing=10)
    side.setFixedWidth(270)
    sv.addWidget(lab("CONTROL", "tileLabel"))
    sv.addWidget(lab("Scenario", "muted"))
    cb = QComboBox()
    cb.addItems(["munich_static.json", "munich_route.json"])
    sv.addWidget(cb)
    sv.addWidget(lab("Device", "muted"))
    dv = QComboBox()
    dv.addItems(["B206mini · 3271A9F", "Simulated SDR"])
    sv.addWidget(dv)
    sv.addWidget(lab("TX gain", "muted"))
    sl = QSlider(Qt.Orientation.Horizontal)
    sl.setRange(0, 89)
    sv.addWidget(sl)
    sv.addWidget(check("Test only (no RF)", True))
    sv.addWidget(check("Shielded setup confirmed", False))
    sv.addStretch(1)
    pb = QProgressBar()
    pb.setValue(42)
    pb.setFormat("04:12 / 10:00")
    sv.addWidget(pb)
    go = QPushButton("▶  Start")
    go.setObjectName("startButton")
    sv.addWidget(go)
    st = QPushButton("■  STOP RF")
    st.setObjectName("estopButton")
    sv.addWidget(st)
    root.addWidget(side)
    return win


# ====================================================================== layout 8: timeline editor
def build_timeline(theme):
    win = QWidget()
    win.setObjectName("central")
    root = QVBoxLayout(win)
    root.setContentsMargins(16, 14, 16, 14)
    root.setSpacing(12)

    bar = QHBoxLayout()
    bar.setSpacing(8)
    bar.addWidget(lab("Scenario timeline", "h1"))
    bar.addSpacing(20)
    for t in ("⏮", "◀◀", "▶", "▶▶", "⏭"):
        b = QPushButton(t)
        b.setObjectName("primary" if t == "▶" else "ghost")
        b.setFixedWidth(52)
        bar.addWidget(b)
    bar.addSpacing(12)
    bar.addWidget(lab("12:04:12 UTC", "bigValue"))
    bar.addStretch(1)
    zoom = QComboBox()
    zoom.addItems(["24 h", "6 h", "1 h", "10 min"])
    bar.addWidget(lab("Zoom", "muted"))
    bar.addWidget(zoom)
    st = QPushButton("■  STOP RF")
    st.setObjectName("estopButton")
    bar.addWidget(st)
    root.addLayout(bar)

    body = QHBoxLayout()
    body.setSpacing(12)
    left = QVBoxLayout()
    left.setSpacing(10)
    tc, tv = card(margins=10, spacing=6)
    tv.addLayout(hbox(lab("Satellite visibility", "h2"), None, legend(theme)))
    tv.addWidget(VisibilityTimeline(theme), 1)
    tv.addWidget(EventLane(theme))
    left.addWidget(tc, 1)
    body.addLayout(left, 1)

    side, sv = card(margins=16, spacing=8)
    side.setFixedWidth(300)
    sv.addWidget(lab("SELECTED EVENT", "tileLabel"))
    sv.addWidget(lab("◆  E12 outage", "h2"))
    f = QFormLayout()
    f.setVerticalSpacing(8)
    ty = QComboBox()
    ty.addItems(["Signal outage", "C/N0 step", "Route leg", "Start / stop"])
    f.addRow("Type", ty)
    f.addRow("Satellite", QLineEdit("E12"))
    f.addRow("At", QLineEdit("07:12:00"))
    f.addRow("Duration", dspin(45, 0, " s"))
    f.addRow("Level", dspin(-14.0, 1, " dB"))
    sv.addLayout(f)
    sv.addWidget(check("Ramp in / out", True))
    sv.addLayout(hbox(QPushButton("Duplicate"), QPushButton("Delete"), None))
    sv.addSpacing(10)
    sv.addWidget(lab("RUN", "tileLabel"))
    for k, v, tone in (("Gen speed", "1.42×", "ok"), ("Gaps", "0", "ok")):
        sv.addLayout(hbox(lab(k, "muted"), None, lab(v, "bigValue", tone=tone)))
    sv.addStretch(1)
    sv.addWidget(check("Test only (no RF)", True))
    go = QPushButton("▶  Run scenario")
    go.setObjectName("startButton")
    sv.addWidget(go)
    body.addWidget(side)
    root.addLayout(body, 1)
    return win


LAYOUTS = {
    "dashboard": ("Sidebar dashboard", build_dashboard, "midnight"),
    "mission": ("Mission control", build_mission, "radar"),
    "wizard": ("Setup wizard", build_wizard, "paper"),
    "map": ("Trajectory map", build_map, "nord"),
    "studio": ("Studio (IDE style)", build_studio, "carbon"),
    "compact": ("Compact panel", build_compact, "glacier"),
    "instruments": ("Instrument panel", build_instruments, "amber"),
    "timeline": ("Scenario timeline", build_timeline, "midnight"),
}
SIZES = {"compact": (480, 900)}


class Main(QMainWindow):
    def __init__(self, themes, layout, theme_id):
        super().__init__()
        self.setWindowTitle(f"SignalSim · {LAYOUTS[layout][0]}")
        self.resize(*SIZES.get(layout, (1360, 860)))
        self.setCentralWidget(LAYOUTS[layout][1](themes[theme_id]))


def arg(name, default=None):
    if name in sys.argv:
        i = sys.argv.index(name)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


def main():
    app = QApplication(sys.argv[:1])
    app.setStyle("Fusion")
    themes = load_themes()
    if "--shots" in sys.argv:
        os.makedirs(SHOTS, exist_ok=True)
        only = arg("--layout")
        jobs = ([(only, t) for t in themes] if only else
                [(k, v[2]) for k, v in LAYOUTS.items()])
        for key, theme_id in jobs:
            apply_theme(app, themes[theme_id])
            w = Main(themes, key, theme_id)
            w.show()
            app.processEvents()
            out = os.path.join(SHOTS, f"pyqt-{key}-{theme_id}.png")
            w.grab().save(out)
            w.close()
            print("wrote", out)
        return
    layout = arg("--layout", "dashboard")
    theme_id = arg("--theme", LAYOUTS[layout][2])
    apply_theme(app, themes[theme_id])
    w = Main(themes, layout, theme_id)
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
