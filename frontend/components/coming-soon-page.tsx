import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { getNavItem } from "@/lib/nav";

/** Placeholder for a route whose micro app hasn't been built yet. */
export function ComingSoonPage({ href }: { href: string }) {
  const item = getNavItem(href);

  return (
    <div className="space-y-8">
      <PageHeader title={item.label} description={item.description} />
      <EmptyState
        icon={item.icon}
        title={`${item.label} is on the way`}
        description={item.description}
        badge={item.phase ? `Coming in Phase ${item.phase}` : undefined}
      />
    </div>
  );
}
