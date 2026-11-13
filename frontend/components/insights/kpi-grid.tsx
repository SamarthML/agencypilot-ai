import {
  DollarSign,
  Gauge,
  MousePointerClick,
  Percent,
  Receipt,
  ShoppingCart,
  Target,
  Users,
  type LucideIcon,
} from "lucide-react";

import { KpiCard } from "@/components/kpi-card";
import { Stagger, StaggerItem } from "@/components/motion";
import { Skeleton } from "@/components/ui/skeleton";
import { formatKpiValue } from "@/lib/format";
import type { Kpi } from "@/lib/types";

const KPI_ICONS: Record<string, LucideIcon> = {
  sessions: Users,
  conversions: Target,
  conversion_rate: Percent,
  revenue: DollarSign,
  spend: Receipt,
  roas: Gauge,
  cpa: MousePointerClick,
  aov: ShoppingCart,
  active_clients: Users,
};

interface KpiTileProps {
  kpi: Kpi;
  period: string;
  /** Shown when the KPI has no delta. */
  footnote?: string;
}

export function KpiTile({ kpi, period, footnote }: KpiTileProps) {
  return (
    <KpiCard
      label={kpi.label}
      value={formatKpiValue(kpi.value, kpi.unit)}
      deltaPct={kpi.delta_pct}
      goodWhen={kpi.good_when}
      icon={KPI_ICONS[kpi.key]}
      period={period}
      footnote={footnote}
    />
  );
}

export function KpiGrid({ kpis, days }: { kpis: Kpi[]; days: number }) {
  return (
    <Stagger className="grid grid-cols-2 gap-3 md:gap-4 xl:grid-cols-4">
      {kpis.map((kpi) => (
        <StaggerItem key={kpi.key}>
          <KpiTile kpi={kpi} period={`vs prior ${days}d`} />
        </StaggerItem>
      ))}
    </Stagger>
  );
}

export function KpiGridSkeleton({ count = 8 }: { count?: number }) {
  return (
    <div className="grid grid-cols-2 gap-3 md:gap-4 xl:grid-cols-4">
      {Array.from({ length: count }, (_, i) => (
        <Skeleton key={i} className="h-[124px] rounded-2xl" />
      ))}
    </div>
  );
}
