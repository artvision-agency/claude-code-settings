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

const KenBurns: React.FC<{src: string; dur: number}> = ({src, dur}) => {
  const f = useCurrentFrame();
  const scale = interpolate(f, [0, dur], [1.05, 1.15], {
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill style={{overflow: "hidden"}}>
      <Img
        src={staticFile(src)}
        style={{width: "100%", height: "100%", objectFit: "cover",
          transform: `scale(${scale})`}}
      />
    </AbsoluteFill>
  );
};

const Slide: React.FC<{lines: string[]}> = ({lines}) => (
  <AbsoluteFill style={{background: "#0f1b2d", color: "#fff",
    padding: "7%", justifyContent: "center", gap: 24,
    fontFamily: "Inter, sans-serif"}}>
    {lines.map((l, i) => (
      <div key={i} style={{fontSize: i === 0 ? 64 : 40,
        color: i === 0 ? "#58a6ff" : "#cdd9e5"}}>{l}</div>
    ))}
  </AbsoluteFill>
);

const Diagram: React.FC<{spec: string}> = ({spec}) => (
  <AbsoluteFill style={{background: "#0a0e14", color: "#2dd4bf",
    padding: "8%", fontFamily: "monospace", fontSize: 34,
    whiteSpace: "pre-wrap"}}>
    {spec}
  </AbsoluteFill>
);

export const Main: React.FC<Props> = ({audioSrc, pip, blocks}) => {
  const m = pip.marginPct * 100;
  return (
    <AbsoluteFill style={{background: "#000"}}>
      {blocks.map((b) => (
        <Sequence key={b.index} from={b.fromFrame}
          durationInFrames={b.durationFrames}>
          {b.marker === "B" && b.imageSrc ? (
            <KenBurns src={b.imageSrc} dur={b.durationFrames} />
          ) : b.marker === "C" ? (
            <Slide lines={b.slideLines ?? []} />
          ) : (
            <Diagram spec={b.diagramSpec ?? ""} />
          )}
        </Sequence>
      ))}
      <Video
        src={staticFile(pip.src)}
        style={{position: "absolute", width: `${pip.widthPct * 100}%`,
          right: `${m}%`, bottom: `${m}%`, borderRadius: 12,
          border: "2px solid #fff"}}
      />
      <Audio src={staticFile(audioSrc)} />
    </AbsoluteFill>
  );
};
