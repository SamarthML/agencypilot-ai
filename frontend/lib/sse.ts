import type { CopilotStreamEvent } from "@/lib/types";

const EVENT_NAMES = new Set<CopilotStreamEvent["event"]>(["token", "citations", "done", "error"]);

export interface SseParseResult {
  events: CopilotStreamEvent[];
  /** Trailing text of an event that hasn't fully arrived yet; prepend it to the next chunk. */
  rest: string;
}

function parseBlock(block: string): CopilotStreamEvent | null {
  let name = "message";
  const data: string[] = [];
  for (const line of block.split(/\r?\n/)) {
    if (line.startsWith("event:")) name = line.slice(6).trim();
    else if (line.startsWith("data:")) data.push(line.slice(5).replace(/^ /, ""));
  }
  if (!EVENT_NAMES.has(name as CopilotStreamEvent["event"]) || data.length === 0) return null;
  return { event: name, data: JSON.parse(data.join("\n")) } as CopilotStreamEvent;
}

/** Split a buffer of Server-Sent Events text into complete events plus the incomplete tail. */
export function parseSseChunk(buffer: string): SseParseResult {
  const blocks = buffer.split(/\r?\n\r?\n/);
  const rest = blocks.pop() ?? "";
  const events = blocks.map(parseBlock).filter((e): e is CopilotStreamEvent => e !== null);
  return { events, rest };
}
