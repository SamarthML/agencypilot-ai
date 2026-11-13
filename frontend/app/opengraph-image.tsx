import { ImageResponse } from "next/og";

import { STAR_PATH, STAR_VIEWBOX } from "@/lib/brand";

export const alt = "AgencyPilot AI: an AI workspace for digital agencies";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const APPS = ["Client Insights", "SEO Audit", "RAG Copilot", "Report Generator"];

/** Social preview card, rendered at build time (no binary asset in the repo). */
export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: 72,
          background: "#09090b",
          backgroundImage: "radial-gradient(circle at 85% 10%, rgba(139,92,246,0.35), transparent 45%)",
          color: "#fafafa",
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          <div
            style={{
              width: 72,
              height: 72,
              borderRadius: 18,
              background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <svg width="44" height="44" viewBox={STAR_VIEWBOX}>
              <path d={STAR_PATH} fill="#ffffff" />
            </svg>
          </div>
          <div style={{ fontSize: 40, fontWeight: 700 }}>AgencyPilot AI</div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <div style={{ fontSize: 68, fontWeight: 700, lineHeight: 1.1, maxWidth: 950 }}>
            The AI workspace for digital agencies
          </div>
          <div style={{ fontSize: 30, color: "#a1a1aa", maxWidth: 950 }}>
            Grounded LLM output, RAG with page citations, and every call tracked for tokens,
            latency and cost.
          </div>
        </div>
        <div style={{ display: "flex", gap: 14 }}>
          {APPS.map((app) => (
            <div
              key={app}
              style={{
                display: "flex",
                padding: "12px 22px",
                borderRadius: 999,
                border: "1px solid #3f3f46",
                background: "#18181b",
                fontSize: 24,
                color: "#e4e4e7",
              }}
            >
              {app}
            </div>
          ))}
        </div>
      </div>
    ),
    size,
  );
}
