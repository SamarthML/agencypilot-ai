import { describe, expect, it } from "vitest";

import { CITE_HREF_PREFIX, citationFor, numberCitations, stripCitations } from "@/lib/citations";
import type { Citation } from "@/lib/types";

const FILES = ["brief.pdf", "notes.md"];

function refsOf(text: string, filenames: readonly string[] = FILES): [string, number][] {
  return numberCitations(text, filenames).refs.map((r) => [r.filename, r.page]);
}

describe("numberCitations refs (mirrors backend citation_refs)", () => {
  it.each<[string, [string, number][]]>([
    ["Budget is $18,000 [brief.pdf p.2].", [["brief.pdf", 2]]],
    ["A [brief.pdf p. 3] and B [brief.pdf p.1].", [["brief.pdf", 3], ["brief.pdf", 1]]],
    ["Both [brief.pdf p.2, p.3].", [["brief.pdf", 2], ["brief.pdf", 3]]],
    ["Mixed [brief.pdf p.2; notes.md p.1].", [["brief.pdf", 2], ["notes.md", 1]]],
    ["Repeated [brief.pdf p.2] twice [brief.pdf p.2].", [["brief.pdf", 2]]],
    ["Page word [brief.pdf page 4].", [["brief.pdf", 4]]],
    ["Unknown file [other.pdf p.2] and a [link](x).", []],
    ["No citations at all.", []],
    // gpt-oss on Groq cites with fullwidth brackets.
    ["Budget **$18,000**【brief.pdf p.2】 and【notes.md p.1】", [["brief.pdf", 2], ["notes.md", 1]]],
  ])("%s", (answer, expected) => {
    expect(refsOf(answer)).toEqual(expected);
  });

  it("does not read page-like text inside a filename as a page", () => {
    expect(refsOf("[p2.pdf p.7]", ["p2.pdf"])).toEqual([["p2.pdf", 7]]);
  });

  it("prefers the longest known filename when one contains another", () => {
    expect(refsOf("[old-brief.pdf p.1]", ["brief.pdf", "old-brief.pdf"])).toEqual([
      ["old-brief.pdf", 1],
    ]);
  });

  it("falls back to anything file-like when the document list is unknown", () => {
    expect(refsOf("See [Q4 plan.pdf p.3] and [data_v2.txt p.1].", [])).toEqual([
      ["plan.pdf", 3],
      ["data_v2.txt", 1],
    ]);
  });

  it("matches filenames case-insensitively", () => {
    expect(refsOf("[BRIEF.PDF p.2]")).toEqual([["BRIEF.PDF", 2]]);
  });
});

describe("numberCitations markdown", () => {
  const link = (n: number) => `[${n}](${CITE_HREF_PREFIX}${n})`;

  it("numbers sources by first mention and reuses numbers for repeats", () => {
    const { markdown } = numberCitations("A [brief.pdf p.2]. B [notes.md p.1]. C [brief.pdf p.2].", FILES);
    expect(markdown).toBe(`A ${link(1)}. B ${link(2)}. C ${link(1)}.`);
  });

  it("expands a multi-page group into adjacent chips without duplicates", () => {
    const { markdown } = numberCitations("Both [brief.pdf p.2, p.3, p.2].", FILES);
    expect(markdown).toBe(`Both ${link(1)}${link(2)}.`);
  });

  it("leaves ordinary markdown links and unknown files untouched", () => {
    const text = "Read [the docs](https://example.com) and [other.pdf p.2].";
    expect(numberCitations(text, FILES).markdown).toBe(text);
  });
});

describe("stripCitations", () => {
  it("removes markers and the space before punctuation", () => {
    expect(stripCitations("Budget is $18,000 [brief.pdf p.2].", FILES)).toBe("Budget is $18,000.");
  });

  it("collapses double spaces left by a mid-sentence marker", () => {
    expect(stripCitations("Ferment 【brief.pdf p.1】 for 36 hours.", FILES)).toBe("Ferment for 36 hours.");
  });

  it("keeps brackets that are not citations", () => {
    expect(stripCitations("Use [x] here [other.pdf p.1].", FILES)).toBe("Use [x] here [other.pdf p.1].");
  });
});

describe("citationFor", () => {
  const citations: Citation[] = [
    { filename: "brief.pdf", page: 2, snippet: "Budget...", similarity: 0.8 },
    { filename: "notes.md", page: 1, snippet: "Notes...", similarity: 0.6 },
  ];

  it("finds the structured citation by file and page, ignoring case", () => {
    expect(citationFor({ filename: "Brief.PDF", page: 2 }, citations)?.snippet).toBe("Budget...");
  });

  it("returns undefined for a missing ref or an uncited page", () => {
    expect(citationFor(undefined, citations)).toBeUndefined();
    expect(citationFor({ filename: "brief.pdf", page: 9 }, citations)).toBeUndefined();
  });
});
