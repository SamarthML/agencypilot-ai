import type { Metadata } from "next";
import { Suspense } from "react";

import { DetailSkeleton, ReportDetail } from "@/components/reports/report-detail";

export const metadata: Metadata = { title: "Report" };

/**
 * The id is only known at request time, so useParams suspends during prerendering (Cache
 * Components); the skeleton is the prerendered fallback.
 */
export default function Page() {
  return (
    <Suspense fallback={<DetailSkeleton />}>
      <ReportDetail />
    </Suspense>
  );
}
