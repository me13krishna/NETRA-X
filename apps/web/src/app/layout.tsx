import type { Metadata } from "next";
import { Archivo, Archivo_Black, JetBrains_Mono } from "next/font/google";
import "./globals.css";

/**
 * Typographic architecture for the Tactical Telemetry substrate.
 *
 * Previously no font was loaded at all -- globals.css declared `font-family:
 * 'Inter'` for a face the browser never received, so every screen fell back to
 * the system sans. Inter-everywhere is also the exact default the design audit
 * flags as an AI fingerprint.
 *
 *   Archivo Black   macro-typography. Structural headers as solid blocks.
 *   Archivo         body and UI text. Same family, so the two never clash.
 *   JetBrains Mono  micro-typography. Carries every hash, fingerprint, wallet
 *                   address, LLR value and unit ID -- the things an analyst
 *                   reads character by character.
 *
 * Self-hosted by next/font at build time, so no runtime request to Google and
 * no flash of unstyled text.
 */
const archivo = Archivo({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-sans",
});

const archivoBlack = Archivo_Black({
  subsets: ["latin"],
  display: "swap",
  weight: "400", // the family ships a single weight; it is already black
  variable: "--font-display",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  display: "swap",
  weight: ["400", "500", "700"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "NETRA-X | Dark Web Threat Actor Intelligence Platform",
  description: "Evidence-Driven Dark Web Threat Actor Intelligence & Attribution Platform",
  icons: {
    icon: "/favicon.ico",
    apple: "/netra-x-logo.png",
  },
  openGraph: {
    title: "NETRA-X",
    description: "Evidence-Driven Dark Web Threat Actor Intelligence & Attribution Platform",
    images: ["/netra-x-logo.png"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${archivo.variable} ${archivoBlack.variable} ${jetbrainsMono.variable}`}
    >
      <body className="bg-netra-bg text-netra-text antialiased">{children}</body>
    </html>
  );
}
