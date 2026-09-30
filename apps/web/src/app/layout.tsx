import type { Metadata } from "next";
import { QueryProvider } from "@/shared/context/query-provider";
import "./globals.css";

export const metadata: Metadata = {
  title: "Renzai",
  description: "Open-source AI Security & Observability Platform",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <QueryProvider>{children}</QueryProvider>
      </body>
    </html>
  );
}
