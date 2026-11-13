import type { Metadata } from "next";

import { SeoView } from "@/components/seo/seo-view";

export const metadata: Metadata = { title: "SEO Audit" };

export default function Page() {
  return <SeoView />;
}
