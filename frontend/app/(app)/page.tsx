import { AppCard } from "@/components/home/app-card";
import { HeroCard } from "@/components/home/hero-card";
import { OnboardingBanner } from "@/components/home/onboarding-banner";
import { OverviewKpis } from "@/components/home/overview-kpis";
import { FadeIn, Stagger, StaggerItem } from "@/components/motion";
import { getNavItem, MICRO_APP_HREFS } from "@/lib/nav";

export default function HomePage() {
  return (
    <div className="space-y-8 md:space-y-10">
      <FadeIn>
        <HeroCard />
      </FadeIn>

      <OnboardingBanner />

      <OverviewKpis />

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
