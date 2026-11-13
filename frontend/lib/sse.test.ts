import { describe, expect, it } from "vitest";

import { parseSseChunk } from "@/lib/sse";

function sse(event: string, data: unknown): string {
  return `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
}

describe("parseSseChunk", () => {
  it("parses a full token → citations → done stream in order", () => {
    const citations = [{ filename: "brief.pdf", page: 2, snippet: "s", similarity: 0.7 }];
    const buffer =
      sse("token", { text: "Hel" }) + sse("token", { text: "lo" }) + sse("citations", { citations }) + sse("done", { x: 1 });

    const { events, rest } = parseSseChunk(buffer);

    expect(events.map((e) => e.event)).toEqual(["token", "token", "citations", "done"]);
    expect(events[1].data).toEqual({ text: "lo" });
    expect(events[2].data).toEqual({ citations });
    expect(rest).toBe("");
  });

  it("keeps an incomplete trailing event as `rest` and completes it with the next chunk", () => {
    const full = sse("token", { text: "one" }) + sse("token", { text: "two" });
    const cut = full.length - 8;

    const first = parseSseChunk(full.slice(0, cut));
    expect(first.events).toHaveLength(1);

    const second = parseSseChunk(first.rest + full.slice(cut));
    expect(second.events).toEqual([{ event: "token", data: { text: "two" } }]);
    expect(second.rest).toBe("");
  });

  it("handles a chunk split inside the blank-line separator", () => {
    const first = parseSseChunk('event: token\ndata: {"text":"a"}\n');
    expect(first.events).toEqual([]);

    const second = parseSseChunk(`${first.rest}\n`);
    expect(second.events).toEqual([{ event: "token", data: { text: "a" } }]);
  });

  it("accepts CRLF line endings", () => {
    const { events } = parseSseChunk('event: token\r\ndata: {"text":"hi"}\r\n\r\n');
    expect(events).toEqual([{ event: "token", data: { text: "hi" } }]);
  });

  it("joins multi-line data fields with newlines before parsing JSON", () => {
    const { events } = parseSseChunk('event: error\ndata: {"detail":\ndata: "boom"}\n\n');
    expect(events).toEqual([{ event: "error", data: { detail: "boom" } }]);
  });

  it("strips only one leading space from data", () => {
    const { events } = parseSseChunk('event: token\ndata:  {"text":" x"}\n\n');
    expect(events[0].data).toEqual({ text: " x" });
  });

  it("drops comments, unknown event names, unnamed messages and events without data", () => {
    const buffer =
      ": keep-alive\n\n" +
      sse("progress", { pct: 50 }) +
      `data: ${JSON.stringify({ text: "no name" })}\n\n` +
      "event: done\n\n" +
      sse("token", { text: "kept" });

    expect(parseSseChunk(buffer).events).toEqual([{ event: "token", data: { text: "kept" } }]);
  });

  it("returns nothing for an empty buffer", () => {
    expect(parseSseChunk("")).toEqual({ events: [], rest: "" });
  });
});
