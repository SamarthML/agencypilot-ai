import type { Metadata, Viewport } from "next";
import { Geist_Mono, Inter } from "next/font/google";

import { Providers } from "@/components/providers";

import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const SITE_NAME = "AgencyPilot AI";
const DESCRIPTION =
  "AI workspace for digital agencies: client insights, SEO audits, a RAG copilot and automated reports, with per-call LLM cost tracking.";

/** Absolute base for Open Graph URLs: Vercel's production domain when deployed, else local dev. */
function siteUrl(): URL {
  const vercelHost = process.env.VERCEL_PROJECT_PRODUCTION_URL;
  return new URL(vercelHost ? `https://${vercelHost}` : "http://localhost:3000");
}

export const metadata: Metadata = {
  metadataBase: siteUrl(),
  applicationName: SITE_NAME,
  title: {
    default: SITE_NAME,
    template: `%s · ${SITE_NAME}`,
  },
  description: DESCRIPTION,
  keywords: ["AI", "LLM", "RAG", "SEO audit", "marketing analytics", "agency", "Next.js", "FastAPI"],
  openGraph: {
    type: "website",
    siteName: SITE_NAME,
    title: SITE_NAME,
    description: DESCRIPTION,
    url: "/",
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    title: SITE_NAME,
    description: DESCRIPTION,
  },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#fafafa" },
    { media: "(prefers-color-scheme: dark)", color: "#09090b" },
  ],
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    // suppressHydrationWarning: next-themes sets the theme class on <html> before hydration.
    <html
      lang="en"
      className={`${inter.variable} ${geistMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <body className="min-h-full">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
