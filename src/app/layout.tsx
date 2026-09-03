import type { Metadata } from "next";
import "./globals.css";
import "./suite-theme.css";
import "./product-pages.css";
import "./workspace-pages.css";
import "./mascot.css";
import "./ingestion-status.css";
import { AuthProvider } from "@/components/auth/AuthProvider";

const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";

export const metadata: Metadata = {
  title: "AutoMinds Africa Bid Finder",
  description: "Uganda procurement intelligence and bid discovery platform.",
  icons: {
    icon: `${basePath}/logo.jpeg`,
    shortcut: `${basePath}/logo.jpeg`,
    apple: `${basePath}/logo.jpeg`,
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
