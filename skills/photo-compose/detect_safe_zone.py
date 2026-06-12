#!/usr/bin/env python3
"""
detect_safe_zone.py — детект лиц на фото → safe-зона для текста → параметры cover-кропа.

Использует ТОЛЬКО установленное: cv2 (haarcascade) + PIL. Без выдуманных либ (proven-tools-first).
Haar — ускоритель, НЕ замена глаз: при пустом результате (профиль/наклон/тёмное) → проверять
скриншот глазами вручную (см. SKILL.md, Шаг 1 fallback).

Usage:
  python3 detect_safe_zone.py <image> [--canvas-w 1080] [--canvas-h 1350]
"""
import sys
import os
import argparse


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--canvas-w", type=int, default=1080)
    ap.add_argument("--canvas-h", type=int, default=1350)
    args = ap.parse_args()

    if not os.path.exists(args.image):
        print(f"ERROR: файл не найден: {args.image}", file=sys.stderr)
        sys.exit(1)

    try:
        import cv2
    except ImportError:
        print("FALLBACK: cv2 недоступен → определи safe-зону визуально (Read скриншота). "
              "См. SKILL.md Шаг 1.", file=sys.stderr)
        sys.exit(2)

    img = cv2.imread(args.image)
    if img is None:
        print(f"ERROR: cv2 не смог прочитать {args.image} (не изображение?)", file=sys.stderr)
        sys.exit(1)
    H, W = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cascade = cv2.CascadeClassifier(
        os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml"))
    faces = cascade.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5,
        minSize=(max(20, int(W * 0.05)), max(20, int(H * 0.05))))

    print(f"Исходник: {W}x{H}px  ratio={W/H:.3f}")
    print(f"Холст:    {args.canvas_w}x{args.canvas_h}px  ratio={args.canvas_w/args.canvas_h:.3f}")

    if len(faces) == 0:
        print("Лиц (frontal) НЕ найдено haar-каскадом.")
        print(">> ВАЖНО: пусто ≠ «лиц нет». Профиль/наклон/тёмное фото haar пропускает.")
        print(">> FALLBACK: посмотри скриншот ГЛАЗАМИ (visual-content R2), определи зону вручную.")
        return

    # bbox каждого лица в %
    print(f"Найдено лиц: {len(faces)}")
    cx_sum = 0.0
    cy_sum = 0.0
    for i, (x, y, w, h) in enumerate(faces, 1):
        print(f"  Лицо {i}: x={x/W*100:.0f}% y={y/H*100:.0f}% "
              f"w={w/W*100:.0f}% h={h/H*100:.0f}% (центр {(x+w/2)/W*100:.0f}%,{(y+h/2)/H*100:.0f}%)")
        cx_sum += (x + w / 2) / W
        cy_sum += (y + h / 2) / H
    cx = cx_sum / len(faces)
    cy = cy_sum / len(faces)

    # Safe-зона для текста = противоположная лицу часть кадра
    horiz = "right" if cx < 0.5 else "left"
    vert = "bottom" if cy < 0.5 else "top"
    print(f"\nЦентр масс лиц: {cx*100:.0f}% по X, {cy*100:.0f}% по Y")
    print(f">> SAFE-ЗОНА для текста/ФИО/плашки/QR: «{vert}» и/или «{horiz}» "
          f"(лицо смещено к {'left' if cx<0.5 else 'right'}-{'top' if cy<0.5 else 'bottom'})")

    # object-position для cover-кропа: держим лицо в кадре, открываем пустую зону под текст
    # cover режет по большей стороне; смещаем позицию к лицу, чтобы оно не срезалось.
    pos_x = "left" if cx < 0.4 else ("right" if cx > 0.6 else "center")
    pos_y = "top" if cy < 0.4 else ("bottom" if cy > 0.6 else "center")
    print(f">> object-fit: cover;  object-position: {pos_x} {pos_y};  (НЕ fill — растянет людей)")
    print(">> После рендера — ПРОВЕРЬ ГЛАЗАМИ: текст ∉ лицо, лицо не срезано, пропорции естественные.")


if __name__ == "__main__":
    main()
