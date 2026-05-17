import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  Sequence,
  Video,
  interpolate,
  staticFile,
  useCurrentFrame,
} from "remotion";

type Block = {
  index: number;
  marker: "B" | "C" | "D";
  title: string;
  fromFrame: number;
  durationFrames: number;
  slideLines: string[] | null;
  diagramSpec: string | null;
  imageSrc: string | null;
};
type Props = {
  audioSrc: string;
  pip: {src: string; widthPct: number; corner: string; marginPct: number};
  blocks: Block[];
};

const BG = "#0e1726";
const FONT =
  '-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Inter,sans-serif';
// Контент держим левее/выше PiP (правый-нижний угол): большой правый и
// нижний отступ — текст/схема никогда не залезают под окошко вебки.
const SAFE: React.CSSProperties = {
  position: "absolute",
  inset: 0,
  padding: "7% 34% 14% 8%",
  display: "flex",
  flexDirection: "column",
  justifyContent: "center",
  overflow: "hidden",
  boxSizing: "border-box",
};

const fadeIn = (f: number) =>
  interpolate(f, [0, 12], [0, 1], {extrapolateRight: "clamp"});

// ── C: слайд (заголовок + тезисы, авто-подгонка кегля, без переполнения) ──
const Slide: React.FC<{title: string; lines: string[]}> = ({title, lines}) => {
  const f = useCurrentFrame();
  const items = (lines ?? []).filter((s) => s && s.trim()).slice(0, 6);
  const bs = items.length <= 3 ? 46 : items.length <= 5 ? 38 : 31;
  return (
    <AbsoluteFill style={{background: BG, fontFamily: FONT}}>
      <div style={{...SAFE, opacity: fadeIn(f)}}>
        <div
          style={{
            color: "#58a6ff",
            fontSize: 62,
            fontWeight: 800,
            lineHeight: 1.12,
            marginBottom: 54,
            letterSpacing: "-0.5px",
          }}
        >
          {title}
        </div>
        <div style={{display: "flex", flexDirection: "column", gap: 28}}>
          {items.map((l, i) => (
            <div
              key={i}
              style={{
                display: "flex",
                gap: 24,
                alignItems: "flex-start",
                color: "#dbe6f2",
                fontSize: bs,
                lineHeight: 1.32,
              }}
            >
              <span
                style={{
                  flex: "none",
                  width: 14,
                  height: 14,
                  marginTop: bs * 0.42,
                  borderRadius: "50%",
                  background: "#58a6ff",
                }}
              />
              <span>{l}</span>
            </div>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ── D: настоящая схема — узлы из diagram_spec, связанные стрелками ──
const parseDiagram = (spec: string, fallbackTitle: string) => {
  let title = fallbackTitle;
  let body = spec ?? "";
  const m = /(^|\n)\s*diagram:\s*(.+)/i.exec(spec ?? "");
  if (m) title = m[2].trim();
  const sm = /(^|\n)\s*source:\s*([\s\S]+)/i.exec(spec ?? "");
  if (sm) body = sm[2];
  const nodes = body
    .split(/;|\n|→|->/)
    .map((s) => s.replace(/^[\s\-–•*]+/, "").trim())
    .filter(Boolean)
    .slice(0, 6);
  return {title, nodes};
};

const Diagram: React.FC<{title: string; spec: string}> = ({title, spec}) => {
  const f = useCurrentFrame();
  const {title: dt, nodes} = parseDiagram(spec, title);
  const ns = nodes.length <= 3 ? 34 : nodes.length <= 5 ? 29 : 25;
  return (
    <AbsoluteFill style={{background: "#0a0f17", fontFamily: FONT}}>
      <div style={{...SAFE, opacity: fadeIn(f)}}>
        <div
          style={{
            color: "#2dd4bf",
            fontSize: 56,
            fontWeight: 800,
            marginBottom: 64,
            letterSpacing: "-0.5px",
          }}
        >
          {dt}
        </div>
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            gap: 22,
          }}
        >
          {nodes.length > 0 ? (
            nodes.map((n, i) => (
              // box + стрелка склеены в неразрывную пару: при переносе
              // стрелка не повисает в начале нового ряда
              <div
                key={i}
                style={{display: "flex", alignItems: "center", gap: 22}}
              >
                <div
                  style={{
                    border: "2px solid #2dd4bf",
                    background: "rgba(45,212,191,0.08)",
                    color: "#e6fffb",
                    borderRadius: 16,
                    padding: "20px 28px",
                    fontSize: ns,
                    lineHeight: 1.25,
                    maxWidth: 360,
                  }}
                >
                  {n}
                </div>
                {i < nodes.length - 1 && (
                  <span style={{color: "#2dd4bf", fontSize: 42}}>→</span>
                )}
              </div>
            ))
          ) : (
            <div
              style={{
                color: "#9fe9df",
                fontSize: 32,
                lineHeight: 1.4,
                whiteSpace: "pre-wrap",
              }}
            >
              {spec}
            </div>
          )}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ── B: фон-картинка с Ken Burns + подпись (нижний-левый, не под PiP) ──
const BImage: React.FC<{title: string; src: string; dur: number}> = ({
  title,
  src,
  dur,
}) => {
  const f = useCurrentFrame();
  const [bad, setBad] = React.useState(false);
  const scale = interpolate(f, [0, dur], [1.06, 1.16], {
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill style={{background: BG, overflow: "hidden", fontFamily: FONT}}>
      {!bad && (
        <Img
          src={staticFile(src)}
          onError={() => setBad(true)}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            transform: `scale(${scale})`,
          }}
        />
      )}
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg,rgba(14,23,38,0) 55%,rgba(14,23,38,0.85) 100%)",
        }}
      />
      <div
        style={{
          position: "absolute",
          left: "8%",
          bottom: "16%",
          maxWidth: "55%",
          color: "#fff",
          fontSize: 54,
          fontWeight: 800,
          textShadow: "0 2px 12px rgba(0,0,0,0.7)",
        }}
      >
        {title}
      </div>
    </AbsoluteFill>
  );
};

export const Main: React.FC<Props> = ({audioSrc, pip, blocks}) => {
  const m = pip.marginPct * 100;
  return (
    <AbsoluteFill style={{background: BG}}>
      {blocks.map((b) => (
        <Sequence
          key={b.index}
          from={b.fromFrame}
          durationInFrames={b.durationFrames}
        >
          {b.marker === "B" && b.imageSrc ? (
            <BImage title={b.title} src={b.imageSrc} dur={b.durationFrames} />
          ) : b.marker === "C" ? (
            <Slide title={b.title} lines={b.slideLines ?? []} />
          ) : (
            <Diagram title={b.title} spec={b.diagramSpec ?? ""} />
          )}
        </Sequence>
      ))}
      <Video
        src={staticFile(pip.src)}
        style={{
          position: "absolute",
          width: `${pip.widthPct * 100}%`,
          right: `${m}%`,
          bottom: `${m}%`,
          borderRadius: 14,
          border: "2px solid rgba(255,255,255,0.9)",
          boxShadow: "0 8px 30px rgba(0,0,0,0.5)",
        }}
      />
      <Audio src={staticFile(audioSrc)} />
    </AbsoluteFill>
  );
};
