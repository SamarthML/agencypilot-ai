import type { Metadata } from "next";

import { ComingSoonPage } from "@/components/coming-soon-page";

export const metadata: Metadata = { title: "Reports" };

export default function Page() {
  return <ComingSoonPage href="/reports" />;
}
