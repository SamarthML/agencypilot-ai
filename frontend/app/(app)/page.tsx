import { DollarSign, SearchCheck, TrendingUp, Users } from "lucide-react";

import { AppCard } from "@/components/home/app-card";
import { HeroCard } from "@/components/home/hero-card";
import { KpiCard } from "@/components/kpi-card";
import { FadeIn, Stagger, StaggerItem } from "@/components/motion";
import { getNavItem, MICRO_APP_HREFS } from "@/lib/nav";

/** Demo numbers until Phase 2 wires the dashboard to real data. */
const DEMO_KPIS = [
  { label: "Active clients", value: "12", deltaPct: 9.1, icon: Users },
  { label: "Monthly ad spend", value: "$48.2k", deltaPct: 8.4, icon: DollarSign },
  { label: "Avg. ROAS", value: "3.6×", deltaPct: 12.5, icon: TrendingUp },
  { label: "Open SEO issues", value: "37", deltaPct: -18.2, icon: SearchCheck, goodWhen: "down" },
] as const;

export default function HomePage() {
  return (
    <div className="space-y-8 md:space-y-10">
      <FadeIn>
        <HeroCard />
      </FadeIn>

      <section aria-labelledby="kpi-heading" className="space-y-4">
        <h2 id="kpi-heading" className="text-sm font-medium text-muted-foreground">
          This month · demo data
        </h2>
        <Stagger className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {DEMO_KPIS.map((kpi) => (
            <StaggerItem key={kpi.label}>
              <KpiCard {...kpi} />
            </StaggerItem>
          ))}
        </Stagger>
      </section>

      <section aria-labelledby="apps-heading" className="space-y-4">
        <h2 id="apps-heading" className="text-sm font-medium text-muted-foreground">
          Micro apps
        </h2>
        <Stagger className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {MICRO_APP_HREFS.map((href) => (
            <StaggerItem key={href}>
              <AppCard item={getNavItem(href)} />
            </StaggerItem>
          ))}
        </Stagger>
      </section>
    </div>
  );
}
