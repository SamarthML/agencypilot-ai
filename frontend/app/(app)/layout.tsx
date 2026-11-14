import { ServerWakeBanner } from "@/components/server-wake-banner";
import { Sidebar } from "@/components/sidebar";
import { Topbar } from "@/components/topbar";

export default function AppLayout({ children }: LayoutProps<"/">) {
  return (
    <div className="flex min-h-svh">
      <a
        href="#main"
        className="sr-only z-50 rounded-lg bg-background px-3 py-2 text-sm font-medium shadow-card ring-2 ring-ring focus:not-sr-only focus:fixed focus:top-3 focus:left-3"
      >
        Skip to content
      </a>
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <ServerWakeBanner />
        <Topbar />
        <main
          id="main"
          tabIndex={-1}
          className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 outline-none md:px-8 md:py-10"
        >
          {children}
        </main>
      </div>
    </div>
  );
}
