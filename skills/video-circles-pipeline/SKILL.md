---
name: video-circles-pipeline
description: |
  Talking-head видеокружки (Loom-style) для встраивания в КП / клиентские дашборды.
  Pipeline: запись на iPhone → нарезка/конкат → crop 720×720 → loudnorm -14 LUFS → poster.jpg → HTML hover-логика (3 стадии: ▶ pulse → muted teaser → Loom-модал с звуком).
  Триггеры (рус/eng): видеокружки, видео кружки, talking head, loom стиль, video commentary, кружки в КП, hover видео, poster preview, монтаж кружков, нарезать ролики антона.
  Reference: https://artvision.pro/mirbir-simple/ (19.05.2026)
---

# Video Circles Pipeline

Когда применять — клиенту в КП/дашборд нужны короткие (15-30 сек) talking-head видеокомментарии Антона / собственника / эксперта по каждому разделу. Loom-style: hover на ▶ → маленькое preview, через 3.5 сек или клик → большой кружок 240×240 в правом нижнем углу со звуком.

## Шаг 1. Запись

Антон записывает на iPhone Pro:
- Вертикально, тихая комната, светлый фон
- 15-30 сек на блок (≈100 слов)
- Голос близко (петличка идеально), один такт без длинных пауз
- Один блок = один MOV ИЛИ один длинный дубль с паузами 1-2 сек (склеим Whisper'ом)

Файлы кидает в `~/Downloads/IMG_xxxx.MOV` (4K HEVC 60fps, 2160×3840 после rotation=90).

## Шаг 2. Опционально — Whisper для timestamps склейки

Если в одном дубле несколько блоков:
```bash
whisper IMG_0159.MOV --model small --language ru --output_format json
```
Открыть `IMG_0159.json` → segments → найти границы фраз → таймкоды для cut.

## Шаг 3. Pipeline скрипт

```bash
~/artvision-data/scripts/video-circles-pipeline.sh <slug> \
  finance=~/Downloads/IMG_0156.MOV \
  market=~/Downloads/IMG_0157.MOV+~/Downloads/IMG_0158.MOV \
  position=~/Downloads/IMG_0159.MOV@0.5,21 \
  channels=~/Downloads/IMG_0159.MOV@22,11.5 \
  shops=~/Downloads/IMG_0159.MOV@34,14.5 \
  planner=~/Downloads/IMG_0159.MOV@50,13
```

Синтаксис аргумента:
- `name=file.MOV` — взять файл целиком
- `name=file.MOV@start,dur` — нарезка от `start` сек длительностью `dur` сек
- `name=fileA+fileB+fileC` — склейка нескольких дублей через concat demuxer

Скрипт делает:
1. ffmpeg cut + crop `1900:1900:0:950` (центрирует лицо при iPhone Pro vertical talking-head) + scale 720×720
2. loudnorm I=-14 LUFS TP=-1.5 LRA=11 (YouTube стандарт)
3. libx264 preset medium CRF 20, pix_fmt yuv420p, r=30, aac 128k, +faststart
4. poster.jpg 200×200 от t=0.5s (статичное превью для UX hint)
5. scp на VPS `/var/www/artvision/<slug>-simple/videos/` + posters/ с retry на SSH моргание

ENV override: `CROP=`, `CRF=`, `LUFS=`, `VPS_HOST=`, `VPS_DIR=`, `SKIP_UPLOAD=1`.

## Шаг 4. HTML pattern

В целевом HTML рядом с каждым H2-блоком вставить anchor:
```html
<h2>Заголовок раздела <span class="video-anchor" data-video="finance.mp4" data-title="Цифры за 90 дней">▶</span></h2>
```

CSS (минимальный, Loom-style):
```css
.video-anchor {
  display: inline-block;
  width: 36px; height: 36px;
  border-radius: 50%;
  background-color: var(--primary); /* fallback пока poster грузится */
  background-size: cover;
  background-position: center top;
  margin-left: 10px;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0,0,0,0.25), inset 0 0 0 2px rgba(255,255,255,0.55);
  vertical-align: middle;
  position: relative;
  user-select: none;
  overflow: hidden;
  transition: transform 0.18s ease;
  font-size: 0;
}
.video-anchor:hover { transform: scale(1.18); box-shadow: 0 4px 14px rgba(225,84,26,0.55), inset 0 0 0 2px rgba(255,255,255,0.7); }
.video-anchor::before {
  content: "▶";
  position: absolute; inset: 0;
  background: rgba(0,0,0,0.55);
  color: #fff; font-size: 14px; line-height: 36px;
  text-align: center;
  border-radius: 50%;
  opacity: 0;
  animation: anchor-play-pulse 3.4s infinite;
}
@keyframes anchor-play-pulse {
  0%, 55% { opacity: 0; }
  62%, 92% { opacity: 1; }
  100% { opacity: 0; }
}
.video-anchor:hover::before { opacity: 1; animation: none; }

/* Loom-style модал bottom-right */
.vid-modal {
  position: fixed; bottom: 28px; right: 28px;
  width: 240px; height: 240px; border-radius: 50%;
  background: linear-gradient(135deg, #1a1a1a 0%, #2a2a2a 100%);
  box-shadow: 0 12px 36px rgba(0,0,0,0.35);
  z-index: 1000; display: none; overflow: hidden;
  animation: vid-pop 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}
@keyframes vid-pop { 0% { transform: scale(0.5); opacity: 0; } 100% { transform: scale(1); opacity: 1; } }
.vid-modal.show { display: block; }
.vid-modal video { width: 100%; height: 100%; object-fit: cover; border-radius: 50%; }

/* Muted teaser рядом с кнопкой */
.vid-teaser {
  position: absolute; width: 120px; height: 120px;
  border-radius: 50%; background: #000;
  box-shadow: 0 8px 24px rgba(0,0,0,0.35);
  z-index: 999; overflow: hidden;
  display: none; pointer-events: none;
}
.vid-teaser.show { display: block; }
.vid-teaser video { width: 100%; height: 100%; object-fit: cover; }
```

JS (с poster injection, 3-stage hover, auto-close):
```js
(function(){
  document.querySelectorAll('.video-anchor').forEach(a=>{
    const name=(a.dataset.video||'').replace(/\.mp4$/,'');
    if(name) a.style.backgroundImage="url('videos/posters/"+name+".jpg')";
  });
  let teaser=null, modal=null, hoverTimer=null, currentAnchor=null;
  function ensureTeaser(){
    if(teaser)return teaser;
    teaser=document.createElement('div'); teaser.className='vid-teaser';
    teaser.innerHTML='<video muted loop playsinline></video>';
    document.body.appendChild(teaser); return teaser;
  }
  function ensureModal(){
    if(modal)return modal;
    modal=document.createElement('div'); modal.className='vid-modal';
    modal.innerHTML='<video playsinline></video>';
    document.body.appendChild(modal);
    const v=modal.querySelector('video');
    v.addEventListener('ended',closeModal);
    modal.addEventListener('click',(e)=>{if(e.target===modal)closeModal();});
    return modal;
  }
  function showTeaser(a){
    const t=ensureTeaser(); const v=t.querySelector('video');
    if(v.src.indexOf(a.dataset.video)===-1) v.src='videos/'+a.dataset.video;
    const r=a.getBoundingClientRect();
    t.style.left=(window.scrollX+r.right+12)+'px';
    t.style.top=(window.scrollY+r.top-50)+'px';
    t.classList.add('show'); v.currentTime=0; v.play().catch(()=>{});
  }
  function hideTeaser(){ if(!teaser)return; teaser.classList.remove('show'); const v=teaser.querySelector('video'); if(v)v.pause(); }
  function openModal(a){
    hideTeaser(); const m=ensureModal(); const v=m.querySelector('video');
    v.src='videos/'+a.dataset.video; v.muted=false;
    m.classList.add('show'); v.play().catch(()=>{});
  }
  function closeModal(){ if(!modal)return; modal.classList.remove('show'); const v=modal.querySelector('video'); if(v){v.pause(); v.src='';} }
  document.addEventListener('mouseover',e=>{
    const a=e.target.closest('.video-anchor'); if(!a||a===currentAnchor)return;
    currentAnchor=a; showTeaser(a); clearTimeout(hoverTimer);
    hoverTimer=setTimeout(()=>openModal(a),3500);
  });
  document.addEventListener('mouseout',e=>{
    const a=e.target.closest('.video-anchor'); if(!a)return;
    if(e.relatedTarget&&e.relatedTarget.closest&&e.relatedTarget.closest('.video-anchor')===a)return;
    currentAnchor=null; hideTeaser(); clearTimeout(hoverTimer);
  });
  document.addEventListener('click',e=>{
    const a=e.target.closest('.video-anchor'); if(!a)return;
    e.preventDefault(); clearTimeout(hoverTimer); openModal(a);
  });
  document.addEventListener('keydown',e=>{if(e.key==='Escape')closeModal();});
})();
```

## Анти-паттерны (узнали 19.05.2026)

| ❌ | ✅ |
|---|---|
| `-ss` ПЕРЕД `-i` на HEVC 4K — ломает aac decoder (`Qavg: nan`, Conversion failed!) | `-ss` ПОСЛЕ `-i` (точный seek через декодирование) |
| `crop=iw:iw:0:(ih-iw)/2` (центр по высоте) — обрезает макушку у iPhone Pro vertical talking-head | `crop=1900:1900:0:950` — лицо центрировано (макушка y≈1160, подбородок y≈2640 в 2160×3840) |
| Полагаться на ui-visual-validator расчёты Y_offset | Замерять на full-size кадре оригинала вручную |
| Не учитывать `rotation=90` metadata | ffmpeg auto-applies — iw=2160 (после rotate), ih=3840 |
| ssh + scp в одной длинной команде — моргание разрывает в середине | Retry-обёртка `scp_retry()` 3 попытки с sleep 2 |
| controls/close/caption в Loom-модале — захламляет | «Просто кружочек фигачит и всё» — auto-close on ended, ESC, клик по фону |
| Размер anchor 22px ▶-символ — не понятно что за кнопкой | 36×36 с poster.jpg + pulse animation = UX hint «за кнопкой видео» |

## Связанные правила и файлы

- `~/.claude/rules/shorts-pip-composition.md` — раздел XII для video circles (отличается от Shorts PiP)
- `~/artvision-data/decisions/2026-05-19-mirbir-video-circles.md` — decision log
- `~/artvision-data/presales/mirbir/mirbir-simple.html` — reference implementation
- `~/artvision-data/scripts/video-circles-pipeline.sh` — bash pipeline
