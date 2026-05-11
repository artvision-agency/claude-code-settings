"""CSS для command-center.html. Вынесено из command-center.py при refactoring 2026-05-10."""

CSS = """
:root { color-scheme: light; --brand: #2c3e88; --bg: #f4f5f7; --card: #fff;
        --critical: #b71c1c; --critical-bg: #fdecea;
        --warning: #e65100; --warning-bg: #fff3e0;
        --good: #1b5e20; --good-bg: #e8f5e9;
        --text: #1a1a1a; --muted: #666; }
* { box-sizing: border-box; }
body { font-family: -apple-system, Segoe UI, Roboto, sans-serif;
       background: var(--bg); color: var(--text); margin: 0; padding: 16px; }
.container { max-width: 1400px; margin: 0 auto; }
header { background: linear-gradient(135deg, var(--brand) 0%, #1e2c5f 100%);
         color: white; padding: 20px 28px; border-radius: 12px;
         margin-bottom: 16px; box-shadow: 0 4px 12px rgba(44,62,136,0.2); }
header h1 { margin: 0 0 4px; font-size: 22px; }
header .meta { font-size: 13px; opacity: 0.85; }
header .badges { margin-top: 8px; }
header .badge { background: rgba(255,255,255,0.2); padding: 3px 10px;
                border-radius: 4px; font-size: 11px; margin-right: 6px;
                font-weight: 600; letter-spacing: 0.5px; }

.alerts { display: grid; grid-template-columns: 1fr; gap: 8px; margin-bottom: 16px; }
.alert { background: var(--critical-bg); border-left: 4px solid var(--critical);
         color: var(--critical); padding: 10px 16px; border-radius: 6px;
         font-weight: 600; font-size: 14px; }
.alert.warning { background: var(--warning-bg); border-color: var(--warning); color: var(--warning); }
.alert.good { background: var(--good-bg); border-color: var(--good); color: var(--good); }
.alert a { color: inherit; }

.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
        gap: 16px; }
.card { background: var(--card); border-radius: 10px; padding: 18px 22px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
.card h2 { margin: 0 0 12px; font-size: 16px; color: var(--brand);
           border-bottom: 1px solid #eee; padding-bottom: 6px;
           display: flex; align-items: center; justify-content: space-between; }
.card h2 .icon { font-size: 18px; margin-right: 8px; }
.card h2 .pill { background: #eef; color: var(--brand); padding: 2px 8px;
                 border-radius: 10px; font-size: 11px; font-weight: 600; }
.metric { display: flex; justify-content: space-between; align-items: baseline;
          padding: 6px 0; border-bottom: 1px dotted #eee; font-size: 13px; }
.metric:last-child { border-bottom: none; }
.metric .label { color: var(--muted); }
.metric .value { font-weight: 700; color: var(--text); font-variant-numeric: tabular-nums; }
.metric .value.big { font-size: 20px; color: var(--brand); }
.metric .value.danger { color: var(--critical); }
.metric .value.warning { color: var(--warning); }
.metric .value.good { color: var(--good); }
.bucket-list { list-style: none; padding: 0; margin: 0; }
.bucket-list li { padding: 5px 0; font-size: 13px;
                  display: flex; justify-content: space-between; }
.bucket-list .count { font-weight: 700; color: var(--brand); }
table.compact { width: 100%; border-collapse: collapse; font-size: 12px; }
table.compact th, table.compact td { padding: 4px 8px; text-align: left;
                                      border-bottom: 1px solid #f0f0f0; }
table.compact th { color: var(--muted); font-weight: 500; }

.research-link { display: block; padding: 8px 12px; margin: 4px 0;
                 background: #f7f8fa; border-left: 3px solid var(--brand);
                 border-radius: 4px; font-size: 13px; text-decoration: none;
                 color: var(--text); }
.research-link:hover { background: #eef; }
.research-link .name { font-weight: 600; }
.research-link .meta { color: var(--muted); font-size: 11px; }

.empty { text-align: center; color: var(--muted); padding: 30px;
         font-size: 13px; font-style: italic; }
.refresh-cmd { background: #1f2937; color: #e5e7eb; padding: 12px 16px;
               border-radius: 6px; font-family: SFMono-Regular, monospace;
               font-size: 12px; margin: 12px 0; overflow-x: auto; }
footer { text-align: center; color: var(--muted); font-size: 11px;
         margin-top: 24px; padding: 16px; }
.tag { display: inline-block; padding: 2px 7px; border-radius: 10px;
       font-size: 11px; font-weight: 600; margin-right: 4px; }
.tag.ok { background: #c8e6c9; color: #1b5e20; }
.tag.crit { background: #ffcdd2; color: #b71c1c; }
.tag.warn { background: #ffe0b2; color: #e65100; }
.tag.neutral { background: #eee; color: #555; }
@media (max-width: 600px) {
  body { padding: 8px; }
  .card { padding: 14px 16px; }
  header { padding: 14px 18px; }
}
"""
