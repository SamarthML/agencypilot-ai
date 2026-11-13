import { ImageResponse } from "next/og";

import { STAR_PATH, STAR_VIEWBOX } from "@/lib/brand";

export const size = { width: 180, height: 180 };
export const contentType = "image/png";

/** iOS home-screen icon: same mark as app/icon.svg, as a PNG (iOS ignores SVG touch icons). */
export default function AppleIcon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
        }}
      >
        <svg width="132" height="132" viewBox={STAR_VIEWBOX}>
          <path d={STAR_PATH} fill="#ffffff" />
        </svg>
      </div>
    ),
    size,
  );
}
