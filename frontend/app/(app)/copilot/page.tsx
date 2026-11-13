import type { Metadata } from "next";

import { CopilotView } from "@/components/copilot/copilot-view";

export const metadata: Metadata = { title: "Copilot" };

export default function Page() {
  return <CopilotView />;
}
