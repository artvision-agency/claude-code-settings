#!/usr/bin/env python3
"""Генерация набора SEO-графиков для КП.

Источник: сессия na-sklad.ru (2026-05-01).
Палитра: PRIMARY=#2c3e88 (синий), DANGER=#c92533 (красный), WARN=#d97706 (жёлтый),
         GREEN=#15803d (зелёный), GREY=#9ca3af.

Usage:
    python3 gen-charts.py --client na-sklad --out /tmp/na-sklad-img/ \\
        --traffic '117:90.93:-' '1900:8:+' '2800:5:+' \\
        --traffic-labels 'na-sklad.ru' 'beelogistic.ru' 'dlg.ru' \\
        --pulse 25 34 14.8 0 \\
        --sitemap '23:8' '59:0' '87:139' \\
        --sitemap-labels 'na-sklad.ru' 'altum-spb.ru' 'dlg.ru' \\
        --backlinks-fresh 23 64 \\
        --backlinks-hist 165 987 \\
        --backlinks-nofollow 92.9 22.5 \\
        --backlinks-labels 'na-sklad.ru' 'dlg.ru'
"""
import argparse
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

PRIMARY = '#2c3e88'
DANGER  = '#c92533'
WARN    = '#d97706'
GREEN   = '#15803d'
GREY    = '#9ca3af'

plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.size'] = 11
plt.rcParams['axes.spines.top'] = False
plt.rcParams['axes.spines.right'] = False


def chart_traffic(out, sites, visits, mom_labels, title='Поисковый трафик'):
    fig, ax = plt.subplots(figsize=(8, 4), dpi=150)
    colors = [DANGER if i == 0 else PRIMARY for i in range(len(sites))]
    bars = ax.barh(sites, visits, color=colors)
    ax.set_xlabel('Визитов в месяц')
    ax.set_title(title, fontsize=12, pad=14)
    ax.invert_yaxis()
    for b, v, m in zip(bars, visits, mom_labels):
        ax.text(v + max(visits) * 0.02, b.get_y() + b.get_height() / 2,
                f'{v:,}  •  {m}', va='center', fontsize=10, fontweight='bold')
    ax.set_xlim(0, max(visits) * 1.4)
    plt.tight_layout()
    plt.savefig(out, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()


def chart_pulse_radar(out, scores, labels=None, target=70):
    """4 модуля: commercial / text / link / behavioral. Score 0-100."""
    if labels is None:
        labels = ['Коммерческие\nфакторы', 'Текстовые\nфакторы',
                  'Ссылочные\nфакторы', 'Поведенческие']
    overall = sum(scores) / len(scores)
    fig, ax = plt.subplots(figsize=(6.2, 6.2), dpi=150, subplot_kw=dict(polar=True))
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    scores_plot = [s if s > 1 else 0.1 for s in scores]
    sc = scores_plot + [scores_plot[0]]
    bm = [target] * len(labels) + [target]
    ang = angles + [angles[0]]
    ax.fill(ang, bm, color=GREEN, alpha=0.10, label=f'Целевой уровень {target}/100')
    ax.plot(ang, bm, color=GREEN, linewidth=1.2, alpha=0.5)
    ax.fill(ang, sc, color=DANGER, alpha=0.30, label=f'Текущий уровень')
    ax.plot(ang, sc, color=DANGER, linewidth=2.4)
    for a, s in zip(angles, scores):
        ax.plot(a, s if s > 1 else 0.1, 'o', color=DANGER, markersize=8, zorder=5)
        ax.annotate(f'{s if s > 1 else "—"}', (a, s if s > 1 else 0.1),
                    textcoords='offset points', xytext=(0, 10),
                    ha='center', fontsize=11, fontweight='bold', color=DANGER)
    ax.set_xticks(angles)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(['20', '40', '60', '80', '100'], fontsize=8, color='#888')
    ax.grid(True, color='#e5e7eb')
    ax.set_title(f'Сводный SEO-аудит — {overall:.1f} из 100', fontsize=13, pad=20, fontweight='bold')
    ax.legend(loc='upper right', bbox_to_anchor=(1.35, 1.10), frameon=False, fontsize=9)
    plt.tight_layout()
    plt.savefig(out, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()


def chart_sitemap_diff(out, sites, pages, posts, title='Объём индексируемого контента'):
    fig, ax = plt.subplots(figsize=(8, 4), dpi=150)
    x = np.arange(len(sites))
    w = 0.36
    b1 = ax.bar(x - w/2, pages, w, label='Страницы услуг', color=PRIMARY)
    b2 = ax.bar(x + w/2, posts, w, label='Посты в блоге', color=GREY)
    ax.set_xticks(x)
    ax.set_xticklabels(sites, fontsize=10)
    ax.set_ylabel('URL в sitemap.xml')
    ax.set_title(title, fontsize=12, pad=14)
    ax.legend(loc='upper left', frameon=False)
    for bars in [b1, b2]:
        for b in bars:
            h = b.get_height()
            if h > 0:
                ax.text(b.get_x() + b.get_width()/2, h + 4, str(int(h)),
                        ha='center', va='bottom', fontsize=10, fontweight='bold')
    ax.set_ylim(0, max(pages + posts) * 1.18)
    plt.tight_layout()
    plt.savefig(out, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()


def chart_backlinks(out, sites, fresh, hist, nofollow_pct, title='Ссылочный профиль'):
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)
    x = np.arange(len(sites))
    w = 0.28
    b1 = ax.bar(x - w, fresh, w, label='Свежие ref.domains', color=PRIMARY)
    b2 = ax.bar(x,     hist,  w, label='Исторические ref.domains', color=GREY)
    b3 = ax.bar(x + w, nofollow_pct, w, label='% nofollow', color=DANGER)
    ax.set_xticks(x)
    ax.set_xticklabels(sites, fontsize=11)
    ax.set_ylabel('Количество доменов / процент')
    ax.set_title(title, fontsize=12, pad=14)
    ax.legend(loc='upper left', frameon=False, fontsize=9)
    max_val = max(max(fresh), max(hist), max(nofollow_pct))
    for bars in [b1, b2, b3]:
        for b in bars:
            h = b.get_height()
            ax.text(b.get_x() + b.get_width()/2, h + max_val * 0.012, f'{h:g}',
                    ha='center', va='bottom', fontsize=9, fontweight='bold')
    ax.set_ylim(0, max_val * 1.15)
    plt.tight_layout()
    plt.savefig(out, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--client', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--traffic', nargs='+', help='visits:mom:sign per site')
    ap.add_argument('--traffic-labels', nargs='+')
    ap.add_argument('--pulse', nargs=4, type=float, metavar=('COMM', 'TEXT', 'LINK', 'BEHAV'))
    ap.add_argument('--sitemap', nargs='+', help='pages:posts per site')
    ap.add_argument('--sitemap-labels', nargs='+')
    ap.add_argument('--backlinks-fresh', nargs='+', type=int)
    ap.add_argument('--backlinks-hist', nargs='+', type=int)
    ap.add_argument('--backlinks-nofollow', nargs='+', type=float)
    ap.add_argument('--backlinks-labels', nargs='+')
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)

    if args.traffic and args.traffic_labels:
        visits, mom_labels = [], []
        for t in args.traffic:
            v, mom, sign = t.split(':')
            visits.append(int(v))
            mom_labels.append(f'{sign}{mom}%')
        chart_traffic(os.path.join(args.out, 'traffic.png'),
                      args.traffic_labels, visits, mom_labels)

    if args.pulse:
        chart_pulse_radar(os.path.join(args.out, 'pulse-radar.png'), args.pulse)

    if args.sitemap and args.sitemap_labels:
        pages, posts = [], []
        for s in args.sitemap:
            p, po = s.split(':')
            pages.append(int(p))
            posts.append(int(po))
        chart_sitemap_diff(os.path.join(args.out, 'sitemap-diff.png'),
                           args.sitemap_labels, pages, posts)

    if all([args.backlinks_fresh, args.backlinks_hist, args.backlinks_nofollow, args.backlinks_labels]):
        chart_backlinks(os.path.join(args.out, 'backlinks.png'),
                        args.backlinks_labels, args.backlinks_fresh,
                        args.backlinks_hist, args.backlinks_nofollow)

    for f in sorted(os.listdir(args.out)):
        sz = os.path.getsize(os.path.join(args.out, f))
        print(f'  ✓ {f}: {sz:,} bytes')


if __name__ == '__main__':
    main()
