import React from "react";
import {Composition, getInputProps} from "remotion";
import {Main} from "./Main";

export const RemotionRoot: React.FC = () => {
  const props = getInputProps() as any;
  const fps = props.fps ?? 30;
  const blocks = props.blocks ?? [];
  const total =
    blocks.length > 0
      ? blocks[blocks.length - 1].fromFrame +
        blocks[blocks.length - 1].durationFrames
      : fps;
  return (
    <Composition
      id="Main"
      component={Main}
      durationInFrames={Math.max(1, total)}
      fps={fps}
      width={props.width ?? 1920}
      height={props.height ?? 1080}
      defaultProps={props}
    />
  );
};
