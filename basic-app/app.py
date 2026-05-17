"""
Auckland Bus Patronage Dashboard — GISCI 343
Research question: Which bus routes serve the Auckland University campus,
and how does patronage vary by route and day of week?

Run: shiny run --reload app.py
"""
from __future__ import annotations
from pathlib import Path
from datetime import date
import warnings
warnings.filterwarnings("ignore")

import geopandas as gpd
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_widget
import ipyleaflet as L
import ipywidgets as widgets

# ── Paths ─────────────────────────────────────────────────────────────────────
HERE      = Path(__file__).parent
RAW       = HERE.parent / "data" / "raw"
PROCESSED = HERE.parent / "data" / "processed"

# ── Colours ───────────────────────────────────────────────────────────────────
BG      = "#1A1A2E"
BG_MID  = "#16213E"
CARD    = "#0F3460"
TEAL    = "#00B4A0"
BLUE    = "#4A90D9"
ORANGE  = "#FF6B35"
TEXT    = "#E0E0E0"
TEXT_DIM= "#9AAAB4"
YELLOW  = "#FFE033"

# Region colours
REGION_COLOURS = {
    "Central": "#4A90D9",   # blue
    "East":    "#00C96B",   # green
    "North":   "#FF4FA0",   # pink
    "South":   "#FF6B35",   # orange
    "West":    "#9B59B6",   # purple
    "Waiheke": "#F1C40F",   # yellow
}

WEEKDAY_ORDER = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
WEEKDAY_SHORT = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]

# ── Load data ─────────────────────────────────────────────────────────────────
print("Loading data...")
routes_gdf  = gpd.read_file(PROCESSED / "routes_uni.gpkg").to_crs(4326)
markers_gdf = gpd.read_file(PROCESSED / "stops_markers.gpkg").to_crs(4326)
routes_gdf["ROUTENUMBER"] = routes_gdf["ROUTENUMBER"].astype(str).str.strip()

uni_row = markers_gdf.iloc[0]
UNI_LAT, UNI_LON = float(uni_row["lat"]), float(uni_row["lon"])

print(f"  Routes: {routes_gdf['ROUTENUMBER'].nunique()} unique")

raw  = pd.read_csv(RAW / "patronage.csv", thousands=",", dtype=str)
meta = ["Route", "Region", "Number"]
date_cols = [c for c in raw.columns if c not in meta]
raw["Number"] = raw["Number"].astype(str).str.strip()
pat = raw.melt(id_vars=meta, value_vars=date_cols, var_name="date_str", value_name="patronage")
pat["date"] = pd.to_datetime(pat["date_str"], dayfirst=True, errors="coerce")
pat = pat.dropna(subset=["date"])
pat["patronage"] = pd.to_numeric(pat["patronage"].astype(str).str.replace(",",""), errors="coerce").fillna(0)
pat["weekday"] = pat["date"].dt.day_name()
# Build region lookup from patronage CSV
route_region = raw.drop_duplicates("Number").set_index("Number")["Region"].to_dict()
# Map region onto routes_gdf
routes_gdf["REGION"] = routes_gdf["ROUTENUMBER"].map(route_region).fillna("Central")
ALL_REGIONS = sorted(routes_gdf["REGION"].unique().tolist())
print(f"  Regions: {ALL_REGIONS}")
print("Ready.\n")

# ── CSS ───────────────────────────────────────────────────────────────────────
CSS = """
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;700&family=Space+Mono:wght@400;700&display=swap');
*, *::before, *::after { box-sizing: border-box; }
body { background: #1A1A2E; color: #E0E0E0; font-family: 'DM Sans', sans-serif; margin: 0; }

.dash-hdr { background: linear-gradient(120deg, #0F3460 0%, #16213E 65%, #1A1A2E 100%);
    border-bottom: 1px solid #00B4A033; padding: 14px 28px;
    display: flex; align-items: center; gap: 14px; }
.hdr-icon { font-size: 22px; background: #00B4A0; width: 38px; height: 38px;
    border-radius: 9px; display: flex; align-items: center; justify-content: center; }
.hdr-title { font-family: 'Space Mono', monospace; font-size: 1rem; font-weight: 700; color: #fff; }
.hdr-sub { font-size: 0.72rem; color: #9AAAB4; margin-top: 2px; }

.bslib-sidebar-layout > .sidebar { background: #16213E !important; border-right: 1px solid #0F3460 !important; }
.sidebar-content { display: flex; flex-direction: column; gap: 12px; padding: 14px; }
.scard { background: #0F3460; border: 1px solid #1a4a7a; border-radius: 10px; padding: 12px; }
.slabel { font-family: 'Space Mono', monospace; font-size: 0.58rem; letter-spacing: 2px;
    color: #9AAAB4; text-transform: uppercase; margin-bottom: 8px; display: block; }
.scard label { color: #E0E0E0 !important; font-size: 0.83rem !important; }
.scard .control-label { color: #9AAAB4 !important; font-size: 0.75rem !important; margin-bottom: 4px !important; }
.scard .shiny-input-container { margin-bottom: 0 !important; }
.scard input[type=date] { background: #1A1A2E !important; border: 1px solid #1a4a7a !important;
    border-radius: 7px !important; color: #E0E0E0 !important; padding: 6px 8px !important;
    width: 100% !important; font-size: 0.81rem !important; }
input[type=date] { background: #1A1A2E !important; border: 1px solid #1a4a7a !important;
    border-radius: 7px !important; color: #E0E0E0 !important; padding: 6px 8px !important;
    font-size: 0.81rem !important; }
.shiny-input-container label { color: #9AAAB4 !important; font-size: 0.76rem !important; }
.scard input[type=radio] { accent-color: #00B4A0; }
.help-card { background: #00B4A00d; border: 1px solid #00B4A028; border-radius: 10px;
    padding: 10px 12px; font-size: 0.76rem; color: #9AAAB4; line-height: 1.55; }
.help-card strong { color: #00B4A0; }
.clear-btn { width: 100%; background: #0F3460; border: 1px solid #1a4a7a; color: #9AAAB4;
    border-radius: 8px; padding: 9px; font-family: 'DM Sans', sans-serif;
    font-size: 0.82rem; cursor: pointer; }
.clear-btn:hover { background: #1a4a7a; color: #E0E0E0; }

.stat-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; padding: 16px; }
.stat-box { background: #0F3460; border: 1px solid #1a4a7a; border-radius: 10px; padding: 14px 16px; }
.stat-label { font-family: 'Space Mono', monospace; font-size: 0.57rem; letter-spacing: 1.8px;
    color: #9AAAB4; text-transform: uppercase; margin-bottom: 5px; }
.stat-value { font-family: 'Space Mono', monospace; font-size: 1.3rem; font-weight: 700;
    color: #00B4A0; line-height: 1.1; }
.stat-sub { font-size: 0.73rem; color: #9AAAB4; margin-top: 3px;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.phdr { background: #16213E; border-bottom: 1px solid #0F3460; padding: 7px 16px;
    font-family: 'Space Mono', monospace; font-size: 0.61rem;
    letter-spacing: 1.6px; color: #9AAAB4; text-transform: uppercase; }
.panel-card { background: #16213E; border: 1px solid #0F3460;
    border-radius: 10px; overflow: hidden; margin: 0 16px 16px 16px; }

table.rt { width: 100%; border-collapse: collapse; font-size: 0.83rem; }
table.rt thead th { background: #0F3460; color: #9AAAB4; padding: 9px 16px;
    text-align: left; font-weight: 600; font-size: 0.73rem; }
table.rt tbody tr { border-bottom: 1px solid #0F3460; cursor: pointer; transition: background 0.12s; }
table.rt tbody tr:hover { background: #0F3460; }
table.rt tbody tr.sel-row { background: #FFE03318; border-left: 3px solid #FFE033; }
table.rt tbody td { padding: 8px 16px; color: #E0E0E0; }
table.rt td.rnum { font-family: 'Space Mono', monospace; font-size: 0.77rem; color: #00B4A0; font-weight: 700; }
table.rt td.rpat { font-family: 'Space Mono', monospace; color: #FF6B35; font-weight: 700; }
"""

# ── UI ────────────────────────────────────────────────────────────────────────
app_ui = ui.page_fluid(
    ui.tags.style(CSS),
    ui.div(
        ui.div("🚌", class_="hdr-icon"),
        ui.div(
            ui.div("Auckland University Bus Patronage Dashboard", class_="hdr-title"),
            ui.div("Which routes serve the university, and when? · 2024 · GISCI 343", class_="hdr-sub"),
        ),
        class_="dash-hdr",
    ),
    ui.layout_sidebar(
        ui.sidebar(
            ui.div(
                ui.div(
                    ui.HTML(
                        "<strong>How to use:</strong> Adjust the date range to filter "
                        "patronage data. Click a row in the table to highlight that "
                        "route on the map. Use the basemap toggle to switch themes."
                    ),
                    class_="help-card",
                ),
                ui.div(
                    ui.tags.span("Regions", class_="slabel"),
                    ui.output_ui("region_checkboxes"),
                    class_="scard",
                ),

                ui.div(
                    ui.tags.span("Basemap", class_="slabel"),
                    ui.input_radio_buttons(
                        "basemap", None,
                        choices={"dark": "🌑 Dark", "light": "☀ Light"},
                        selected="dark",
                    ),
                    class_="scard",
                ),
                ui.tags.button(
                    "✕  Clear selected route", id="btn_clear", class_="clear-btn",
                    onclick="Shiny.setInputValue('btn_clear', Math.random(), {priority:'event'})",
                ),
                class_="sidebar-content",
            ),
            width=230,
        ),


        ui.layout_columns(
            ui.div(
                ui.div("🗺  Route Map — click a row to highlight a route", class_="phdr"),
                output_widget("map_widget"),
                class_="panel-card",
                style="margin:0;",
            ),
            ui.div(
                ui.div("📋  Route Summary — click to highlight on map", class_="phdr"),
                ui.output_ui("route_table"),
                class_="panel-card",
                style="margin:0; overflow-y:auto; max-height:494px;",
            ),
            col_widths=[7, 5],
            style="padding: 0 16px 16px 16px; gap: 16px;",
        ),

        ui.div(
            ui.div(
                ui.div(
                    ui.input_date(
                        "date_from", "From",
                        value=date(2024, 1, 1),
                        min=date(2024, 1, 1), max=date(2024, 12, 31),
                        format="dd/mm/yyyy",
                    ),
                    style="flex:1;",
                ),
                ui.div(
                    ui.input_date(
                        "date_to", "To",
                        value=date(2024, 12, 31),
                        min=date(2024, 1, 1), max=date(2024, 12, 31),
                        format="dd/mm/yyyy",
                    ),
                    style="flex:1;",
                ),
                ui.output_ui("stat_boxes_inline"),
                style="display:flex; align-items:flex-end; gap:16px; flex-wrap:wrap;",
            ),
            style=(
                "background:#0F3460; border:1px solid #1a4a7a; border-radius:10px;"
                "padding:14px 20px; margin:0 16px 16px 16px;"
            ),
        ),

        ui.div(
            ui.div("📊  Average Daily Patronage by Route", class_="phdr"),
            ui.output_plot("route_chart", height="320px"),
            class_="panel-card",
        ),
    ),
    ui.tags.script("""
        var _sel = '';
        $(document).on('click', 'tr[data-route]', function () {
            var r = String($(this).data('route'));
            _sel = (_sel === r) ? '' : r;
            Shiny.setInputValue('clicked_route', _sel, {priority:'event'});
        });
    """),
)

# ── Server ────────────────────────────────────────────────────────────────────
def server(input, output, session):

    selected = reactive.Value(None)

    @output
    @render.ui
    def region_checkboxes():
        boxes = []
        for region in ALL_REGIONS:
            colour = REGION_COLOURS.get(region, BLUE)
            boxes.append(
                ui.div(
                    ui.input_checkbox(
                        f"region_{region}", 
                        ui.HTML(f"<span style='color:{colour};font-weight:600;'>{region}</span>"),
                        value=True
                    ),
                    style="margin-bottom:2px;"
                )
            )
        return ui.div(*boxes)

    @reactive.effect
    @reactive.event(input.btn_clear)
    def _clear():
        selected.set(None)

    @reactive.effect
    @reactive.event(input.clicked_route)
    def _pick():
        v = input.clicked_route()
        selected.set(v.strip() if v and v.strip() else None)

    # ── Shared calcs ──────────────────────────────────────────────────────────

    @reactive.calc
    def active_regions():
        return [r for r in ALL_REGIONS
                if input[f"region_{r}"]()]

    @reactive.calc
    def cur_routes_filtered():
        """Routes filtered by active regions."""
        regions = active_regions()
        return routes_gdf[routes_gdf["REGION"].isin(regions)]

    @reactive.calc
    def cur_pat():
        """Patronage filtered by date range and region — shared by table, chart and stats."""
        nums  = cur_routes_filtered()["ROUTENUMBER"].unique().tolist()
        start = pd.Timestamp(input.date_from())
        end   = pd.Timestamp(input.date_to())
        return pat[pat["Number"].isin(nums) & pat["date"].between(start, end)]

    @reactive.calc
    def cur_table():
        """Avg daily patronage per route — shared by table and chart."""
        df = cur_pat()
        if df.empty:
            return pd.DataFrame(columns=["Route #", "Route Name", "Region", "Avg Daily Patronage"])
        agg = (df.groupby(["Number","Route","Region"])["patronage"].mean().reset_index()
               .rename(columns={"Number":"Route #","Route":"Route Name","patronage":"Avg Daily Patronage"}))
        agg["Avg Daily Patronage"] = agg["Avg Daily Patronage"].round(0).astype(int)
        return agg.sort_values("Avg Daily Patronage", ascending=False).reset_index(drop=True)

    # ── Stat boxes ────────────────────────────────────────────────────────────

    @output
    @render.ui
    def stat_boxes_inline():
        df  = cur_table()
        sub = cur_pat()
        n   = cur_routes_filtered()["ROUTENUMBER"].nunique()

        top_num, top_name, avg = "—", "", "—"
        if not df.empty:
            top_num  = str(df.iloc[0]["Route #"])
            top_name = df.iloc[0]["Route Name"]
        if not sub.empty:
            avg = f"{int(sub.groupby('date')['patronage'].sum().mean()):,}"
        short = (top_name[:28] + "…") if len(top_name) > 28 else top_name

        return ui.HTML(f"""
        <div style="display:flex; gap:12px; flex:3;">
            <div class="stat-box" style="flex:1;">
                <div class="stat-label">Routes</div>
                <div class="stat-value">{n}</div>
                <div class="stat-sub">serving campus</div>
            </div>
            <div class="stat-box" style="flex:2;">
                <div class="stat-label">Top Route</div>
                <div class="stat-value">Route {top_num}</div>
                <div class="stat-sub">{short}</div>
            </div>
            <div class="stat-box" style="flex:1;">
                <div class="stat-label">Avg Daily</div>
                <div class="stat-value">{avg}</div>
                <div class="stat-sub">boardings</div>
            </div>
        </div>
        """)

    # ── Map ───────────────────────────────────────────────────────────────────

    @output
    @render_widget
    def map_widget():
        basemap = (L.basemaps.CartoDB.Positron if input.basemap() == "light"
                   else L.basemaps.CartoDB.DarkMatter)
        m = L.Map(
            basemap=basemap,
            center=[UNI_LAT, UNI_LON],
            zoom=13,
            scroll_wheel_zoom=True,
            layout=widgets.Layout(height="480px", width="100%"),
        )

        sel     = selected()
        sel_str = str(sel).strip() if sel else None
        gdf     = cur_routes_filtered()

        # Draw one GeoJSON layer per region so each gets its own colour
        highlight = []
        for region in ALL_REGIONS:
            region_gdf = gdf[gdf["REGION"] == region]
            if region_gdf.empty:
                continue
            colour = REGION_COLOURS.get(region, BLUE)
            normal_feats = []
            for _, row in region_gdf.iterrows():
                rnum = str(row["ROUTENUMBER"]).strip()
                feat = {
                    "type": "Feature",
                    "geometry": row.geometry.__geo_interface__,
                    "properties": {"route": rnum, "name": str(row.get("ROUTENAME",""))},
                }
                if sel_str and rnum == sel_str:
                    highlight.append(feat)
                else:
                    normal_feats.append(feat)
            if normal_feats:
                m.add(L.GeoJSON(
                    data={"type":"FeatureCollection","features":normal_feats},
                    style={"color": colour, "weight": 2, "opacity": 0.85},
                ))

        if highlight:
            m.add(L.GeoJSON(
                data={"type":"FeatureCollection","features":highlight},
                style={"color": YELLOW, "weight": 6, "opacity": 1.0},
            ))

        # University marker
        cm = L.CircleMarker(
            location=[UNI_LAT, UNI_LON],
            radius=10, color="white", weight=2,
            fill_color=TEAL, fill_opacity=1,
        )
        cm.popup = L.Popup(
            child=widgets.HTML(
                "<div style='font-family:sans-serif;padding:4px'>"
                "<b style='color:#00B4A0'>Auckland Universities</b><br>"
                "<span style='color:#555'>Stop B/C/D/E · UoA · AUT</span></div>"
            ),
        )
        m.add(cm)
        return m

    # ── Route bar chart ───────────────────────────────────────────────────────

    @output
    @render.plot
    def route_chart():
        df  = cur_table()
        sel = selected()

        if df.empty:
            fig, ax = plt.subplots(figsize=(10, 3.5))
            fig.patch.set_facecolor(BG_MID)
            ax.set_facecolor(BG_MID)
            ax.text(0.5, 0.5, "No data", transform=ax.transAxes,
                    ha="center", va="center", color=TEXT_DIM, fontsize=12)
            return fig

        n   = len(df)
        fig, ax = plt.subplots(figsize=(max(8, n * 0.55), 3.5))
        fig.patch.set_facecolor(BG_MID)
        ax.set_facecolor(BG_MID)
        fig.subplots_adjust(left=0.09, right=0.98, top=0.83, bottom=0.18)

        colors = []
        for _, row in df.iterrows():
            if str(row["Route #"]) == str(sel):
                colors.append(YELLOW)
            else:
                region = row.get("Region", "Central")
                colors.append(REGION_COLOURS.get(region, BLUE))
        bars = ax.bar(range(n), df["Avg Daily Patronage"].values,
                      color=colors, width=0.65, edgecolor="none", zorder=3)

        mx = df["Avg Daily Patronage"].max() or 1
        for bar, val in zip(bars, df["Avg Daily Patronage"].values):
            ax.text(bar.get_x() + bar.get_width()/2, val + mx * 0.01,
                    f"{int(val):,}", ha="center", va="bottom",
                    fontsize=6.5, color=TEXT, fontweight="bold")

        ax.set_xticks(range(n))
        ax.set_xticklabels(df["Route #"].tolist(), fontsize=7.5, color=TEXT_DIM)
        ax.set_title("Average daily patronage by route",
                     color=TEXT, fontsize=10, fontweight="bold", pad=8)
        from matplotlib.patches import Patch
        legend_handles = [Patch(color=REGION_COLOURS.get(r, BLUE), label=r)
                          for r in active_regions()]
        if sel:
            legend_handles.append(Patch(color=YELLOW, label="Selected"))
        if legend_handles:
            ax.legend(handles=legend_handles, facecolor=CARD, edgecolor=BG_MID,
                      labelcolor=TEXT, fontsize=7.5, loc="upper right")
        ax.set_ylabel("Avg boardings", color=TEXT_DIM, fontsize=9)
        ax.tick_params(axis="y", colors=TEXT_DIM, labelsize=8)
        ax.tick_params(axis="x", colors=TEXT_DIM, length=0)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
        for sp in ax.spines.values(): sp.set_visible(False)
        ax.grid(axis="y", color="#223355", linestyle="--", linewidth=0.5, zorder=0)
        ax.set_ylim(0, mx * 1.18)
        return fig

    # ── Table ─────────────────────────────────────────────────────────────────

    @output
    @render.ui
    def route_table():
        df  = cur_table()
        sel = selected()
        if df.empty:
            return ui.p("No data for current filters.", style="color:#9AAAB4;padding:16px;")
        rows = ""
        for _, row in df.iterrows():
            rnum   = str(row["Route #"]).strip()
            rname  = row["Route Name"]
            region = row.get("Region", "")
            pval   = int(row["Avg Daily Patronage"])
            cls    = "sel-row" if (sel and rnum == sel) else ""
            rows += (f'<tr class="{cls}" data-route="{rnum}">'
                     f'<td class="rnum">{rnum}</td>'
                     f'<td>{rname}</td>'
                     f'<td style="color:#9AAAB4;font-size:0.78rem;">{region}</td>'
                     f'<td class="rpat">{pval:,}</td>'
                     f'</tr>')
        return ui.HTML(
            '<table class="rt"><thead><tr>'
            '<th>Route #</th><th>Route Name</th><th>Region</th><th>Avg Daily Patronage</th>'
            f'</tr></thead><tbody>{rows}</tbody></table>'
        )

app = App(app_ui, server)