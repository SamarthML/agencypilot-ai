import {
  BarChart3,
  FileText,
  Gauge,
  House,
  MessagesSquare,
  SearchCheck,
  Settings,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  /** One-line description of what the page / micro app does. */
  description: string;
}

export const NAV_ITEMS: readonly NavItem[] = [
  {
    href: "/",
    label: "Home",
    icon: House,
    description: "Your agency at a glance.",
  },
  {
    href: "/insights",
    label: "Insights",
    icon: BarChart3,
    description:
      "Upload a client CSV to get KPIs, trend charts and an AI summary written only from the computed numbers.",
  },
  {
    href: "/seo",
    label: "SEO Audit",
    icon: SearchCheck,
    description:
      "Scan any URL against 10 rule-based SEO checks, get a 0–100 score and AI-written fix suggestions.",
  },
  {
    href: "/copilot",
    label: "Copilot",
    icon: MessagesSquare,
    description:
      "Chat with a client's PDFs: answers stream in with page-level citations, grounded by RAG.",
  },
  {
    href: "/reports",
    label: "Reports",
    icon: FileText,
    description:
      "Generate a monthly client report from dashboard data, edit it section by section and export to PDF.",
  },
  {
    href: "/usage",
    label: "Usage",
    icon: Gauge,
    description:
      "Every LLM call with tokens, latency and cost, broken down by provider, model and feature.",
  },
  {
    href: "/settings",
    label: "Settings",
    icon: Settings,
    description: "Provider keys status, default model and workspace preferences.",
  },
];

/** The four micro apps featured on the home page. */
export const MICRO_APP_HREFS = ["/insights", "/seo", "/copilot", "/reports"] as const;

export function getNavItem(href: string): NavItem {
  const item = NAV_ITEMS.find((navItem) => navItem.href === href);
  if (!item) throw new Error(`Unknown nav item: ${href}`);
  return item;
}

export function isActivePath(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}

export function findNavItemForPath(pathname: string): NavItem | undefined {
  return NAV_ITEMS.find((item) => isActivePath(pathname, item.href));
}
