#!/usr/bin/env python3
"""Читает заливку (цвет) ячеек .xlsx детерминированно, без OCR/LLM.
Usage: parse_colors.py <file.xlsx> [sheet_name]
Выводит ячейки с НЕ-пустой/НЕ-белой заливкой + ARGB + группировку по цвету.
Стратегия: openpyxl если есть, иначе stdlib zipfile + xml.etree (fallback).
Покрывает СТАТИЧНУЮ заливку (patternFill). Conditional formatting — НЕ покрывает.
"""
import sys, zipfile
from collections import defaultdict
from xml.etree import ElementTree as ET

WHITE = {"FFFFFFFF", "00000000", "FFFFFF", None, ""}


def via_openpyxl(path, sheet):
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb[sheet] if sheet else wb.active
    out = []
    for row in ws.iter_rows():
        for c in row:
            f = c.fill
            if f is not None and f.patternType:
                rgb = getattr(f.fgColor, "rgb", None)
                if isinstance(rgb, str) and rgb.upper() not in WHITE:
                    out.append((c.coordinate, rgb.upper()))
    return ws.title, out


def via_zip(path, sheet):
    # fallback: парс styles.xml + sheetN.xml вручную
    NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    z = zipfile.ZipFile(path)
    styles = ET.fromstring(z.read("xl/styles.xml"))
    # fills → список fgColor rgb по fillId
    fills = []
    fb = styles.find(f"{NS}fills")
    for fill in fb.findall(f"{NS}fill"):
        pf = fill.find(f"{NS}patternFill")
        rgb = None
        if pf is not None and pf.get("patternType") not in (None, "none"):
            fg = pf.find(f"{NS}fgColor")
            if fg is not None:
                rgb = fg.get("rgb")
        fills.append(rgb)
    # cellXfs → fillId по styleIndex
    cellxfs = []
    cx = styles.find(f"{NS}cellXfs")
    for xf in cx.findall(f"{NS}xf"):
        cellxfs.append(int(xf.get("fillId", "0")))
    # найти нужный sheet файл
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    sheets = wb.find(f"{NS}sheets").findall(f"{NS}sheet")
    target = None
    for i, sh in enumerate(sheets):
        if sheet is None or sh.get("name") == sheet:
            target = i + 1
            tname = sh.get("name")
            break
    if target is None:
        target = 1; tname = sheets[0].get("name")
    data = z.read(f"xl/worksheets/sheet{target}.xml")
    ws = ET.fromstring(data)
    out = []
    for c in ws.iter(f"{NS}c"):
        s = c.get("s")
        if s is None:
            continue
        fid = cellxfs[int(s)] if int(s) < len(cellxfs) else 0
        rgb = fills[fid] if fid < len(fills) else None
        if isinstance(rgb, str) and rgb.upper() not in WHITE:
            out.append((c.get("r"), rgb.upper()))
    return tname, out


def main():
    if len(sys.argv) < 2:
        print("Usage: parse_colors.py <file.xlsx> [sheet]"); sys.exit(1)
    path = sys.argv[1]
    sheet = sys.argv[2] if len(sys.argv) > 2 else None
    try:
        tname, out = via_openpyxl(path, sheet)
        engine = "openpyxl"
    except ImportError:
        tname, out = via_zip(path, sheet)
        engine = "zipfile-fallback"
    except Exception as e:
        # openpyxl есть, но упал → fallback
        tname, out = via_zip(path, sheet)
        engine = f"zipfile-fallback (openpyxl err: {e})"
    print(f"# Лист: {tname} | движок: {engine} | залитых ячеек: {len(out)}")
    by_color = defaultdict(list)
    for cell, rgb in out:
        by_color[rgb].append(cell)
    for rgb, cells in sorted(by_color.items()):
        print(f"{rgb}: {', '.join(cells)}")


if __name__ == "__main__":
    main()
