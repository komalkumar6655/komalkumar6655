# SignalSim GUI – themes and alternative PyQt layouts

## PyQt6 layouts (`pyqt/signalsim_layouts.py`)

Eight different GUI designs for the GNSS signal simulator, each shown with a modern theme:

| Layout | Theme | Screenshot |
|---|---|---|
| Sidebar dashboard: nav rail, KPI cards, sky plot, C/N0 chart | Midnight Indigo | `screenshots/pyqt-dashboard-midnight.png` |
| Mission control: sky, spectrum + waterfall, channel table, event log | Radar | `screenshots/pyqt-mission-radar.png` |
| Setup wizard: 5 steps, constellation cards, band summary | Paper Light | `screenshots/pyqt-wizard-paper.png` |
| Trajectory map: route with floating control cards | Nord Frost | `screenshots/pyqt-map-nord.png` |
| Studio (IDE style): explorer tree, C/N0 timeline, spectrum, inspector | Carbon | `screenshots/pyqt-studio-carbon.png` |
| Compact panel: narrow window, speed gauge, signal chips | Glacier Light | `screenshots/pyqt-compact-glacier.png` |
| Instrument panel: arc gauges + satellite cards | Amber Night | `screenshots/pyqt-instruments-amber.png` |
| Scenario timeline: 24 h visibility bars, event keyframes, event editor | Midnight Indigo | `screenshots/pyqt-timeline-midnight.png` |

```bash
pip install PyQt6
python3 pyqt/signalsim_layouts.py --layout mission            # open a layout
python3 pyqt/signalsim_layouts.py --layout wizard --theme amber
python3 pyqt/signalsim_layouts.py --shots                     # regenerate screenshots
```

Layouts: `dashboard`, `mission`, `wizard`, `map`, `studio`, `compact`, `instruments`, `timeline`. All data shown is demo data.

## Themes (`themes/`)

`themes.json` holds 7 colour themes (carbon, midnight, nord, radar, amber, paper, glacier);
`signalsim.qss` is a stylesheet template whose `{{token}}` placeholders are filled from them.
Any layout works with any theme via `--theme <id>`.

`preview/preview.py` (PySide6) renders the original single-window layout in every theme
(`screenshots/<theme>.png`, `screenshots/gallery.png`).
