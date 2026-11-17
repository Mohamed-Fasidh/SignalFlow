import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Plus_Jakarta_Sans, Roboto, Roboto_Mono } from "next/font/google";
import "./globals.css";

const jakarta = Plus_Jakarta_Sans({ subsets: ["latin"], weight: ["400", "500", "600"], variable: "--font-jakarta", display: "swap" });
const roboto = Roboto({ subsets: ["latin"], weight: ["400", "500"], variable: "--font-roboto", display: "swap" });
const robotoMono = Roboto_Mono({ subsets: ["latin"], weight: ["400", "500"], variable: "--font-roboto-mono", display: "swap" });

export const metadata: Metadata = {
  title: "SignalFlow AI | Revenue intelligence",
  description: "A revenue intelligence workspace for account prioritization, buying signals and CRM workflows.",
  applicationName: "SignalFlow AI",
  keywords: ["revenue intelligence", "GTM", "account prioritization", "buying signals"]
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return <html lang="en"><body className={`${jakarta.variable} ${roboto.variable} ${robotoMono.variable}`}>{children}</body></html>;
}
