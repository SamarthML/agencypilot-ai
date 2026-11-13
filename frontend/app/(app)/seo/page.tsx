import type { Metadata } from "next";

import { ComingSoonPage } from "@/components/coming-soon-page";

export const metadata: Metadata = { title: "SEO Audit" };

export default function Page() {
  return <ComingSoonPage href="/seo" />;
}
