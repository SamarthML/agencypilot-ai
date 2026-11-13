import type { Metadata } from "next";

import { ComingSoonPage } from "@/components/coming-soon-page";

export const metadata: Metadata = { title: "Copilot" };

export default function Page() {
  return <ComingSoonPage href="/copilot" />;
}
