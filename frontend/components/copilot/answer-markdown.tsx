"use client";

import type { ReactNode } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

import { CITE_HREF_PREFIX } from "@/lib/citations";

interface AnswerMarkdownProps {
  markdown: string;
  renderCitation: (n: number) => ReactNode;
}

const STATIC_COMPONENTS: Components = {
  p: ({ children }) => <p className="leading-relaxed [&:not(:first-child)]:mt-3">{children}</p>,
  ul: ({ children }) => <ul className="mt-2 list-disc space-y-1 pl-5 first:mt-0">{children}</ul>,
  ol: ({ children }) => <ol className="mt-2 list-decimal space-y-1 pl-5 first:mt-0">{children}</ol>,
  li: ({ children }) => <li className="leading-relaxed marker:text-muted-foreground">{children}</li>,
  strong: ({ children }) => <strong className="font-semibold text-foreground">{children}</strong>,
  h1: ({ children }) => <h3 className="mt-4 font-semibold first:mt-0">{children}</h3>,
  h2: ({ children }) => <h3 className="mt-4 font-semibold first:mt-0">{children}</h3>,
  h3: ({ children }) => <h4 className="mt-3 font-semibold first:mt-0">{children}</h4>,
  blockquote: ({ children }) => (
    <blockquote className="mt-3 border-l-2 pl-3 text-muted-foreground">{children}</blockquote>
  ),
  code: ({ children }) => <code className="rounded bg-muted px-1 py-0.5 font-mono text-[0.85em]">{children}</code>,
  pre: ({ children }) => (
    <pre className="mt-3 overflow-x-auto rounded-lg bg-muted p-3 text-xs [&_code]:bg-transparent [&_code]:p-0">
      {children}
    </pre>
  ),
  table: ({ children }) => (
    <div className="mt-3 overflow-x-auto rounded-lg border">
      <table className="w-full text-left text-xs">{children}</table>
    </div>
  ),
  th: ({ children }) => <th className="border-b bg-muted/50 px-3 py-2 font-medium whitespace-nowrap">{children}</th>,
  td: ({ children }) => <td className="border-b px-3 py-2 align-top last:border-b-0">{children}</td>,
  hr: () => <hr className="my-4 border-border" />,
};

/** Assistant answer as GitHub-flavoured markdown; `#cite-n` links render as citation chips. */
export function AnswerMarkdown({ markdown, renderCitation }: AnswerMarkdownProps) {
  const components: Components = {
    ...STATIC_COMPONENTS,
    a: ({ href, children }) => {
      if (href?.startsWith(CITE_HREF_PREFIX)) return renderCitation(Number(href.slice(CITE_HREF_PREFIX.length)));
      return (
        <a href={href} target="_blank" rel="noreferrer" className="font-medium underline underline-offset-2">
          {children}
        </a>
      );
    },
  };
  return (
    <div className="text-sm [overflow-wrap:anywhere]">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {markdown}
      </ReactMarkdown>
    </div>
  );
}
