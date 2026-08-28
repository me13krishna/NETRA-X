import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "NETRA-X | Dark Web Threat Actor Intelligence Platform",
  description: "Evidence-Driven Dark Web Threat Actor Intelligence & Attribution Platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="bg-netra-bg text-netra-text antialiased">{children}</body>
    </html>
  );
}
