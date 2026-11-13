"use client";

import { ArrowDown, ArrowUp, Plus, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

interface TextEditorProps {
  id: string;
  label: string;
  value: string;
  max: number;
  onChange: (value: string) => void;
  className?: string;
  placeholder?: string;
}

export function TextEditor({ id, label, value, max, onChange, className, placeholder }: TextEditorProps) {
  const over = value.length > max;
  return (
    <div className="space-y-1">
      <label htmlFor={id} className="sr-only">
        {label}
      </label>
      <Textarea
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        aria-invalid={over || undefined}
        className={cn("bg-background leading-relaxed", className)}
      />
      <p className={cn("text-right text-[11px] tabular-nums text-muted-foreground", over && "text-destructive")}>
        {value.length}/{max}
      </p>
    </div>
  );
}

interface ListEditorProps {
  id: string;
  label: string;
  items: string[];
  min: number;
  max: number;
  itemMax: number;
  onChange: (items: string[]) => void;
}

function move(items: string[], from: number, to: number): string[] {
  const next = [...items];
  const [item] = next.splice(from, 1);
  next.splice(to, 0, item);
  return next;
}

/** Edit a bullet list: change, reorder, add and remove items within the allowed count. */
export function ListEditor({ id, label, items, min, max, itemMax, onChange }: ListEditorProps) {
  return (
    <div className="space-y-2">
      <ol className="space-y-2">
        {items.map((item, index) => (
          <li key={index} className="flex items-start gap-2">
            <span className="mt-2 w-5 shrink-0 text-right text-xs font-medium text-muted-foreground tabular-nums">
              {index + 1}.
            </span>
            <label htmlFor={`${id}-${index}`} className="sr-only">
              {label} item {index + 1}
            </label>
            <Textarea
              id={`${id}-${index}`}
              value={item}
              onChange={(e) => onChange(items.map((old, i) => (i === index ? e.target.value : old)))}
              aria-invalid={item.length > itemMax || !item.trim() || undefined}
              className="min-h-10 min-w-0 flex-1 bg-background leading-relaxed"
            />
            <div className="flex shrink-0 flex-col gap-0.5 sm:flex-row">
              <Button
                type="button" variant="ghost" size="icon-sm" disabled={index === 0}
                onClick={() => onChange(move(items, index, index - 1))} aria-label={`Move ${label} item ${index + 1} up`}
              >
                <ArrowUp aria-hidden />
              </Button>
              <Button
                type="button" variant="ghost" size="icon-sm" disabled={index === items.length - 1}
                onClick={() => onChange(move(items, index, index + 1))} aria-label={`Move ${label} item ${index + 1} down`}
              >
                <ArrowDown aria-hidden />
              </Button>
              <Button
                type="button" variant="ghost" size="icon-sm" disabled={items.length <= min}
                onClick={() => onChange(items.filter((_, i) => i !== index))} aria-label={`Remove ${label} item ${index + 1}`}
                className="hover:text-destructive"
              >
                <X aria-hidden />
              </Button>
            </div>
          </li>
        ))}
      </ol>
      <div className="flex items-center justify-between gap-2 pl-7">
        <Button type="button" variant="outline" size="sm" disabled={items.length >= max} onClick={() => onChange([...items, ""])}>
          <Plus data-icon="inline-start" aria-hidden /> Add item
        </Button>
        <span className="text-[11px] text-muted-foreground">
          {min}-{max} items
        </span>
      </div>
    </div>
  );
}
