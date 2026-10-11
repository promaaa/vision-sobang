"""Write the parts list as an English HTML table from docs/hardware/bom_extinction.csv."""
import csv, html, sys
from collections import OrderedDict

NAMES = [
    "Seaflo SFDP1-010-040-21 12 V diaphragm pump (3.8 L/min, 0.28 MPa), 1 + 1 spare",
    "Nalgene 1 L wide-mouth bottle (fits the printed cradle)",
    "Braided PVC hose, 8 mm inner diameter, per metre",
    "Brass fitting, PT 1/4 male to 8 mm barb (hose to nozzle)",
    "Brass coupling, PT 1/4 female-female",
    "Hose clamp, 8–12 mm",
    "Sanga SJN02 solid-stream nozzle, PT 1/4, 2 mm orifice (pack of 10)",
    "Daiso electric water gun (about 100 mL, first test)",
    "Rechargeable electric water gun, 400 mL (demonstration)",
    "Waveshare ST3215 12 V serial bus servo (30 kg·cm), pan and tilt",
    "Waveshare Bus Servo Adapter (A), USB to servo bus",
    "6808 bearing (40 × 52 × 7 mm), pan axis",
    "M5 T-nuts for 2020 profile (pack of 100)",
    "M3 × 4 mm heat-set inserts (pack of 50)",
    "M4 brass inserts",
    "DC-DC converter, 20–96 V to 12 V, 10 A, waterproof",
    "Raspberry Pi Pico 2 (relay control)",
    "2-channel 5 V relay module (channel 1: gun trigger, channel 2: pump)",
    "SB560 Schottky diode (pump flyback)",
    "NEXT UH305 powered USB 3.0 hub",
    "Adafruit 3626 DC power meter (100 V, 20 A), to measure the current",
    "22 mm latching e-stop, 2 NO + 2 NC (KSEP2260-22)",
    "Power relay, 24 V coil, 30 A",
    "Inline blade fuse holder",
    "Blade fuse, 10 A",
    "Blade fuse, 5 A",
    "ABC powder extinguisher, 3.3 kg (for the tests)",
    "XT30 connector pair (tap on the robot 24 V bus)",
    "XT60 connector pair",
    "Silicone cable 16 AWG, per metre (2 m red + 2 m black), plus 2,800 KRW shipping",
    "DC jack 5.5 × 2.1 mm with cable",
    "Dupont wires (65 pieces)",
    "Heat-shrink tubing (100 pieces)",
    "22 AWG UL1007 wire kit",
    "Third ST3215 servo as a spare",
    "ST3215 from a Korean shop (if the order from abroad is a problem)",
    "KITZ 3/8\" Y-strainer for the pump inlet (heavy)",
]
GROUPS = {"Eau": "Water", "Visée": "Aiming", "Électronique": "Electronics", "Sécurité": "Safety",
          "Câblage": "Wiring", "Optionnel (hors total)": "Optional, not in the total"}


def price_note(s):
    if s.startswith("vérifié"):
        return "checked " + str(int(s.split()[1][-2:])) + " Oct"
    if "Devicemart" in s:
        return "price of 8 Oct"
    return "USD × 1,400"


rows = list(csv.DictReader(open(sys.argv[1], encoding="utf-8")))
assert len(rows) == len(NAMES), (len(rows), len(NAMES))
groups = OrderedDict()
out = ['<div class="scroll"><table class="wide">',
       '<tr><th>Group</th><th>Item</th><th class="r">Qty</th><th class="r">Total (KRW)</th><th>Shop</th><th>Price</th></tr>']
span = {}
for r in rows:
    span[GROUPS[r["catégorie"]]] = span.get(GROUPS[r["catégorie"]], 0) + 1
seen = set()
for r, name in zip(rows, NAMES):
    g = GROUPS[r["catégorie"]]
    gcell = "" if g in seen else f'<th rowspan="{span[g]}">{g}</th>'
    seen.add(g)
    total = int(r["total_krw"])
    if not g.startswith("Optional"):
        groups[g] = groups.get(g, 0) + total
    out.append(f'<tr>{gcell}<td>{html.escape(name)}</td><td class="r">{r["qté"]}</td>'
               f'<td class="r">{total:,}</td><td><a href="{html.escape(r["lien"])}">{html.escape(r["boutique"].replace(" (étranger)", ""))}</a></td>'
               f'<td>{price_note(r["statut_du_prix"])}</td></tr>')
out.append("</table></div>")
grand = sum(groups.values())
assert grand == 463273, grand
summary = ['<div class="scroll"><table>', '<tr><th>Group</th><th class="r">KRW</th></tr>']
summary += [f'<tr><td>{g}</td><td class="r">{v:,}</td></tr>' for g, v in groups.items()]
summary += [f'<tr class="total"><td>Total</td><td class="r">{grand:,}</td></tr>',
            '</table></div>']
page = open(sys.argv[2], encoding="utf-8").read()
page = page.replace("<!--BOM-SUMMARY-->", "\n".join(summary)).replace("<!--BOM-->", "\n".join(out))
open(sys.argv[3], "w", encoding="utf-8").write(page)
