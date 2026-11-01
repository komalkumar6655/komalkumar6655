#!/usr/bin/env python3
"""Render screenshots of every SignalSim theme.

Builds a replica of the SignalSim "simple" window (header, Receiver, Simulation,
Signals, Output, status tiles, Start) with PySide6 and styles it with the *same*
themes.json + signalsim.qss that ThemeManager uses in the C++ app, so each
screenshot shows exactly what the stylesheet produces in Qt.

    pip install PySide6-Essentials
    QT_QPA_PLATFORM=offscreen python3 preview/preview.py            # all themes
    QT_QPA_PLATFORM=offscreen python3 preview/preview.py carbon     # one theme

Output: screenshots/<id>.png, screenshots/gallery.png, screenshots/theme-menu.png
"""
import json
import os
import re
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_SCALE_FACTOR", "1.5")

from PySide6.QtCore import QDateTime, QPoint, QPointF, QRect, Qt
from PySide6.QtGui import (QAction, QActionGroup, QColor, QFont, QFontDatabase, QImage,
                           QPainter, QPainterPath, QPalette, QPen)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDateTimeEdit,
                               QDoubleSpinBox, QFormLayout, QFrame, QGridLayout, QGroupBox,
                               QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMenu,
                               QProgressBar, QPushButton, QRadioButton, QSlider, QSpinBox,
                               QTabWidget, QToolButton, QVBoxLayout, QWidget)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THEMES = os.path.join(ROOT, "themes")
SHOTS = os.path.join(ROOT, "screenshots")

UI_FONTS = ["Inter", "Segoe UI Variable Text", "Segoe UI", "SF Pro Text", "Cantarell", "Noto Sans", "DejaVu Sans"]
MONO_FONTS = ["JetBrains Mono", "Cascadia Mono", "Consolas", "SF Mono", "DejaVu Sans Mono"]


# ------------------------------------------------------------------ theme engine (mirrors ThemeManager.cpp)
def first_family(candidates):
    have = set(QFontDatabase.families())
    for f in candidates:
        if f in have:
            return f
    return candidates[-1]


def _icon(path, draw):
    img = QImage(32, 32, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    draw(p)
    p.end()
    img.save(path, "PNG")


def _stroke(color, points, width):
    def draw(p):
        p.setPen(QPen(QColor(color), width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        path = QPainterPath(QPointF(*points[0]))
        for pt in points[1:]:
            path.lineTo(*pt)
        p.drawPath(path)
    return draw


def make_icons(theme, icon_dir):
    """Check mark and chevrons drawn with QPainter (no SVG plugin needed). Same shapes as ThemeManager.cpp."""
    c = theme["colors"]
    out = {}
    for key, color, pts, width in (
            ("checkIcon", c["accentText"], [(8, 16.5), (13.5, 22), (24, 10.5)], 4.2),
            ("arrowDown", c["textMuted"], [(9, 12), (16, 19), (23, 12)], 3.6),
            ("arrowUp", c["textMuted"], [(9, 20), (16, 13), (23, 20)], 3.6),
            ("arrowDownAccent", c["accent"], [(9, 12), (16, 19), (23, 12)], 3.6)):
        path = os.path.join(icon_dir, f"{theme['id']}-{key}.png")
        _icon(path, _stroke(color, pts, width))
        out[key] = path.replace(os.sep, "/")
    return out


def build_stylesheet(theme, template, icon_dir):
    tokens = dict(theme["colors"])
    os.makedirs(icon_dir, exist_ok=True)
    tokens.update(make_icons(theme, icon_dir))
    tokens["font"] = first_family(UI_FONTS)
    tokens["mono"] = first_family(MONO_FONTS)

    def sub(m):
        key = m.group(1)
        if key not in tokens:
            raise KeyError(f"theme '{theme['id']}' has no value for {{{{{key}}}}}")
        return tokens[key]
    return re.sub(r"\{\{(\w+)\}\}", sub, template)


def build_palette(theme):
    c = {k: QColor(v) for k, v in theme["colors"].items()}
    pal = QPalette()
    pal.setColor(QPalette.Window, c["bg"])
    pal.setColor(QPalette.WindowText, c["text"])
    pal.setColor(QPalette.Base, c["surface2"])
    pal.setColor(QPalette.AlternateBase, c["surface"])
    pal.setColor(QPalette.Text, c["text"])
    pal.setColor(QPalette.PlaceholderText, c["textFaint"])
    pal.setColor(QPalette.Button, c["surface2"])
    pal.setColor(QPalette.ButtonText, c["text"])
    pal.setColor(QPalette.Highlight, c["accent"])
    pal.setColor(QPalette.HighlightedText, c["accentText"])
    pal.setColor(QPalette.ToolTipBase, c["surface"])
    pal.setColor(QPalette.ToolTipText, c["text"])
    pal.setColor(QPalette.Link, c["accent"])
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        pal.setColor(QPalette.Disabled, role, c["textFaint"])
    return pal


# ------------------------------------------------------------------ replica window
def form(rows):
    f = QFormLayout()
    f.setHorizontalSpacing(12)
    f.setVerticalSpacing(8)
    f.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    for label, w in rows:
        f.addRow(label, w)
    return f


def dspin(value, decimals, suffix, lo=-1e9, hi=1e9):
    s = QDoubleSpinBox()
    s.setRange(lo, hi)
    s.setDecimals(decimals)
    s.setValue(value)
    s.setSuffix(suffix)
    return s


def tile(label, value, sub, level=None):
    t = QFrame()
    t.setObjectName("tile")
    if level:
        t.setProperty("level", level)
    v = QVBoxLayout(t)
    v.setContentsMargins(14, 10, 14, 10)
    v.setSpacing(2)
    a = QLabel(label.upper())
    a.setObjectName("tileLabel")
    b = QLabel(value)
    b.setObjectName("tileValue")
    if level:
        b.setProperty("level", level)
    c = QLabel(sub)
    c.setObjectName("tileSub")
    v.addWidget(a)
    v.addWidget(b)
    v.addWidget(c)
    return t


class Window(QMainWindow):
    def __init__(self, themes, current):
        super().__init__()
        self.setWindowTitle("GNSS Simulator")
        self.resize(1280, 780)
        menu = self.menuBar()
        for name in ("&File", "&View", "&Tools", "&Help"):
            menu.addMenu(name)

        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # header -------------------------------------------------------
        header = QFrame()
        header.setObjectName("headerBar")
        h = QHBoxLayout(header)
        h.setContentsMargins(18, 10, 14, 10)
        h.setSpacing(10)
        titles = QVBoxLayout()
        titles.setSpacing(0)
        t = QLabel("\U0001F6F0  GNSS Simulator")
        t.setObjectName("appTitle")
        st = QLabel("SignalSim · multi-GNSS IQ generator · USRP B2xx")
        st.setObjectName("appSubtitle")
        titles.addWidget(t)
        titles.addWidget(st)
        h.addLayout(titles)
        h.addStretch(1)
        badge = QLabel("●  RF OFF · TEST ONLY")
        badge.setObjectName("rfBadge")
        badge.setProperty("state", "off")
        h.addWidget(badge)
        save = QPushButton("\U0001F4BE  Save")
        save.setObjectName("themeToggle")
        h.addWidget(save)
        self.themeButton = QToolButton()
        self.themeButton.setObjectName("themeToggle")
        self.themeButton.setText(f"\U0001F3A8  {current['name']}  ▾")
        self.themeButton.setPopupMode(QToolButton.InstantPopup)
        self.themeMenu = QMenu(self.themeButton)
        group = QActionGroup(self.themeMenu)
        for th in themes:
            a = QAction(("☾  " if th["dark"] else "☀  ") + th["name"], self.themeMenu)
            a.setCheckable(True)
            a.setChecked(th["id"] == current["id"])
            group.addAction(a)
            self.themeMenu.addAction(a)
        self.themeMenu.addSeparator()
        self.themeMenu.addAction("Next theme\tCtrl+T")
        self.themeButton.setMenu(self.themeMenu)
        h.addWidget(self.themeButton)
        stop = QPushButton("■  STOP RF")
        stop.setObjectName("estopButton")
        h.addWidget(stop)
        root.addWidget(header)

        body = QWidget()
        b = QVBoxLayout(body)
        b.setContentsMargins(18, 8, 18, 16)
        b.setSpacing(12)
        root.addWidget(body, 1)

        cols = QHBoxLayout()
        cols.setSpacing(14)
        b.addLayout(cols, 1)

        # column 1: receiver + simulation -----------------------------
        c1 = QVBoxLayout()
        c1.setSpacing(4)
        rec = QGroupBox("RECEIVER")
        rv = QVBoxLayout(rec)
        tabs = QTabWidget()
        static = QWidget()
        static.setLayout(form([
            ("Latitude", dspin(48.137154, 6, " °", -90, 90)),
            ("Longitude", dspin(11.576124, 6, " °", -180, 180)),
            ("Altitude", dspin(520.0, 1, " m")),
            ("Duration", dspin(600, 0, " s", 1, 86400)),
        ]))
        static.layout().setContentsMargins(0, 12, 0, 0)
        tabs.addTab(static, "Static")
        tabs.addTab(QWidget(), "Trajectory")
        rv.addWidget(tabs)
        c1.addWidget(rec)

        sim = QGroupBox("SIMULATION")
        start = QDateTimeEdit(QDateTime.fromString("2026-11-01 12:00:00", "yyyy-MM-dd HH:mm:ss"))
        start.setDisplayFormat("yyyy-MM-dd  HH:mm:ss")
        eph = QHBoxLayout()
        eph.setSpacing(6)
        ephEdit = QLineEdit("EphData/BRDC00WRD_S_20263050000_01D_MN.rnx")
        eph.addWidget(ephEdit, 1)
        eph.addWidget(QPushButton("…"))
        dl = QPushButton("⤓")
        dl.setToolTip("Download today's broadcast ephemeris")
        eph.addWidget(dl)
        ephW = QWidget()
        ephW.setLayout(eph)
        eph.setContentsMargins(0, 0, 0, 0)
        cn0 = dspin(45.0, 1, " dB-Hz", 20, 60)
        el = dspin(5, 0, " °", 0, 90)
        sim.setLayout(form([("Start (UTC)", start), ("Ephemeris", ephW), ("C/N0", cn0), ("Elevation mask", el)]))
        c1.addWidget(sim)
        c1.addStretch(1)
        cols.addLayout(c1, 11)

        # column 2: signals ----------------------------------------------
        c2 = QVBoxLayout()
        c2.setSpacing(4)
        sig = QGroupBox("SIGNALS")
        sg = QGridLayout()
        sg.setHorizontalSpacing(14)
        sg.setVerticalSpacing(10)
        bands = [
            ("GPS", [("L1CA", True), ("L1C", False), ("L2C", False), ("L5", False)]),
            ("Galileo", [("E1", True), ("E5a", False), ("E5b", False)]),
            ("BeiDou", [("B1I", True), ("B1C", False), ("B2a", False), ("B2b", False)]),
            ("GLONASS", [("G1", False), ("G2", False)]),
        ]
        for r, (system, sigs) in enumerate(bands):
            lab = QLabel(system)
            lab.setObjectName("hint")
            sg.addWidget(lab, r, 0)
            for c, (name, on) in enumerate(sigs):
                cb = QCheckBox(name)
                cb.setChecked(on)
                sg.addWidget(cb, r, c + 1)
        sv = QVBoxLayout(sig)
        sv.addLayout(sg)
        sv.addSpacing(6)
        opts = QHBoxLayout()
        a1 = QCheckBox("Auto centre / rate")
        a1.setChecked(True)
        a2 = QCheckBox("SDR exact rate")
        a2.setChecked(True)
        opts.addWidget(a1)
        opts.addWidget(a2)
        opts.addStretch(1)
        sv.addLayout(opts)
        centre = dspin(1568.260, 3, " MHz")
        centre.setEnabled(False)
        rate = dspin(19.35, 2, " MS/s")
        rate.setEnabled(False)
        sv.addLayout(form([("Centre", centre), ("Sample rate", rate)]))
        hint = QLabel("Band 1559.05 – 1577.47 MHz · 23 signals in view")
        hint.setObjectName("hint")
        sv.addWidget(hint)
        c2.addWidget(sig)
        c2.addStretch(1)
        cols.addLayout(c2, 10)

        # column 3: output -------------------------------------------------
        c3 = QVBoxLayout()
        c3.setSpacing(4)
        out = QGroupBox("OUTPUT")
        ov = QVBoxLayout(out)
        modes = QHBoxLayout()
        r1 = QRadioButton("IQ file")
        r2 = QRadioButton("Live SDR")
        r2.setChecked(True)
        modes.addWidget(r1)
        modes.addWidget(r2)
        modes.addStretch(1)
        ov.addLayout(modes)
        sdr = QHBoxLayout()
        sdr.setSpacing(6)
        dev = QComboBox()
        dev.addItems(["B206mini · serial 3271A9F", "Simulated SDR (no RF)"])
        sdr.addWidget(dev, 1)
        sdr.addWidget(QPushButton("Find"))
        sdrW = QWidget()
        sdrW.setLayout(sdr)
        sdr.setContentsMargins(0, 0, 0, 0)
        port = QComboBox()
        port.addItems(["TX/RX", "RX2"])
        gain = QHBoxLayout()
        sl = QSlider(Qt.Horizontal)
        sl.setRange(0, 89)
        sl.setValue(0)
        gl = QLabel("0 dB")
        gl.setMinimumWidth(42)
        gain.addWidget(sl, 1)
        gain.addWidget(gl)
        gW = QWidget()
        gW.setLayout(gain)
        gain.setContentsMargins(0, 0, 0, 0)
        fmt = QComboBox()
        fmt.addItems(["IQ16", "IQ8", "IQ4"])
        fmt.setEnabled(False)
        ov.addLayout(form([("SDR", sdrW), ("TX port", port), ("TX gain", gW), ("IQ format", fmt)]))
        t1 = QCheckBox("Test only (no RF output)")
        t1.setChecked(True)
        t2 = QCheckBox("Shielded / cabled setup confirmed")
        ov.addWidget(t1)
        ov.addWidget(t2)
        c3.addWidget(out)
        c3.addStretch(1)
        cols.addLayout(c3, 10)

        # tiles -------------------------------------------------------------
        tiles = QHBoxLayout()
        tiles.setSpacing(12)
        tiles.addWidget(tile("Generator speed", "1.42×", "real time needs ≥ 1.05×", "ok"))
        tiles.addWidget(tile("Signal gaps", "0", "underruns since start", "ok"))
        tiles.addWidget(tile("Satellites", "23", "GPS 9 · GAL 7 · BDS 7", "info"))
        tiles.addWidget(tile("Sample rate", "19.35", "MS/s · centre 1568.26 MHz"))
        tiles.addWidget(tile("Buffer", "64 %", "target 50–90 %", "warn"))
        tiles.addWidget(tile("Elapsed", "04:12", "of 10:00"))
        b.addLayout(tiles)

        # bottom bar --------------------------------------------------------
        bottom = QHBoxLayout()
        bottom.setSpacing(12)
        info = QVBoxLayout()
        info.setSpacing(6)
        pb = QProgressBar()
        pb.setValue(42)
        pb.setFormat("42 %  ·  04:12 / 10:00")
        info.addWidget(pb)
        okc = current["colors"]["ok"]
        status = QLabel(f"<span style='color:{okc}'>●</span>&nbsp; Running on Simulated SDR · "
                        "ephemeris BRDC00WRD (today, 305) · 4 threads")
        status.setObjectName("statusLine")
        info.addWidget(status)
        bottom.addLayout(info, 1)
        go = QPushButton("▶  Start")
        go.setObjectName("startButton")
        go.setMinimumWidth(150)
        bottom.addWidget(go, 0, Qt.AlignBottom)
        b.addLayout(bottom)


# ------------------------------------------------------------------ gallery
def gallery(themes, out_path):
    thumbs = [(th, QImage(os.path.join(SHOTS, f"{th['id']}.png"))) for th in themes]
    cols = 2
    tw = 900
    th_h = int(thumbs[0][1].height() * tw / thumbs[0][1].width())
    pad, cap = 40, 64
    rows = (len(thumbs) + cols - 1) // cols
    W = cols * tw + (cols + 1) * pad
    H = rows * (th_h + cap) + (rows + 1) * pad + 70
    img = QImage(W, H, QImage.Format_ARGB32)
    img.fill(QColor("#0A0C10"))
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    f = QFont(first_family(UI_FONTS))
    f.setPixelSize(34)
    f.setBold(True)
    p.setFont(f)
    p.setPen(QColor("#E6E8EE"))
    p.drawText(QRect(pad, 24, W, 50), Qt.AlignLeft | Qt.AlignVCenter, "SignalSim GUI — theme gallery")
    for i, (th, im) in enumerate(thumbs):
        r, c = divmod(i, cols)
        x = pad + c * (tw + pad)
        y = 90 + pad + r * (th_h + cap + pad)
        scaled = im.scaled(tw, th_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        clip = QPainterPath()
        clip.addRoundedRect(x, y, tw, th_h, 14, 14)
        p.save()
        p.setClipPath(clip)
        p.drawImage(x, y, scaled)
        p.restore()
        p.setPen(QPen(QColor("#2A2F3A"), 2))
        p.drawPath(clip)
        sw = 22
        for k, key in enumerate(("bg", "surface", "accent", "ok", "warn", "err")):
            p.setPen(QPen(QColor("#3A4150"), 1))
            p.setBrush(QColor(th["colors"][key]))
            p.drawEllipse(x + tw - (6 - k) * (sw + 6), y + th_h + 18, sw, sw)
        f.setPixelSize(26)
        p.setFont(f)
        p.setPen(QColor("#E6E8EE"))
        p.drawText(QRect(x, y + th_h + 10, tw, 40), Qt.AlignLeft | Qt.AlignVCenter,
                   th["name"] + ("  ·  dark" if th["dark"] else "  ·  light"))
    p.end()
    img.save(out_path)


def main():
    data = json.load(open(os.path.join(THEMES, "themes.json"), encoding="utf-8"))
    template = open(os.path.join(THEMES, "signalsim.qss"), encoding="utf-8").read()
    themes = data["themes"]
    wanted = sys.argv[1:] or [t["id"] for t in themes]
    app = QApplication(sys.argv[:1])
    app.setStyle("Fusion")
    icon_dir = os.path.join(tempfile.gettempdir(), "signalsim-theme-icons")
    os.makedirs(SHOTS, exist_ok=True)
    for th in themes:
        if th["id"] not in wanted:
            continue
        app.setPalette(build_palette(th))
        app.setStyleSheet(build_stylesheet(th, template, icon_dir))
        w = Window(themes, th)
        w.show()
        app.processEvents()
        w.grab().save(os.path.join(SHOTS, f"{th['id']}.png"))
        if th["id"] == data["default"]:
            m = w.themeMenu
            m.adjustSize()
            m.popup(w.themeButton.mapToGlobal(QPoint(0, w.themeButton.height() + 4)))
            app.processEvents()
            m.grab().save(os.path.join(SHOTS, "theme-menu.png"))
            m.close()
        w.close()
        print("rendered", th["id"])
    if len(wanted) == len(themes):
        gallery(themes, os.path.join(SHOTS, "gallery.png"))
        print("rendered gallery")


if __name__ == "__main__":
    main()
