/**
 * Channel -> series colour. Colour follows the entity, never its rank: known channels always get
 * the same slot, so switching period or client never repaints a channel.
 */
const KNOWN_CHANNELS = ["Organic", "Paid Search", "Paid Social", "Email", "Referral", "Direct"];
const SLOT_COUNT = 8;
const OTHER = "var(--series-other)";

function slotColor(slot: number): string {
  return `var(--series-${slot + 1})`;
}

/** Stable colours for a dataset's channels; unknown channels take the free slots in name order. */
export function channelColors(channels: readonly string[]): Record<string, string> {
  const colors: Record<string, string> = {};
  const unknown = channels.filter((c) => !KNOWN_CHANNELS.includes(c)).sort();
  for (const channel of channels) {
    const known = KNOWN_CHANNELS.indexOf(channel);
    const slot = known >= 0 ? known : KNOWN_CHANNELS.length + unknown.indexOf(channel);
    colors[channel] = slot < SLOT_COUNT ? slotColor(slot) : OTHER;
  }
  return colors;
}

/** Channels in legend order: known channels first (fixed order), then the rest by name. */
export function orderChannels(channels: readonly string[]): string[] {
  const known = KNOWN_CHANNELS.filter((c) => channels.includes(c));
  const unknown = channels.filter((c) => !KNOWN_CHANNELS.includes(c)).sort();
  return [...known, ...unknown];
}
