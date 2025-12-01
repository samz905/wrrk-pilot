import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "WRRK - AI-Powered Lead Prospecting",
    template: "%s | WRRK",
  },
  description: "Find high-intent leads with AI-powered prospecting. Discover decision-makers actively looking for solutions like yours across Reddit, LinkedIn, Twitter, and more.",
  keywords: ["lead generation", "prospecting", "sales intelligence", "B2B leads", "intent signals", "AI prospecting", "sales automation"],
  authors: [{ name: "WRRK" }],
  creator: "WRRK",
  publisher: "WRRK",
  robots: {
    index: true,
    follow: true,
  },
  openGraph: {
    type: "website",
    locale: "en_US",
    url: "https://wrrk-pilot.vercel.app",
    siteName: "WRRK",
    title: "WRRK - AI-Powered Lead Prospecting",
    description: "Find high-intent leads with AI-powered prospecting. Discover decision-makers actively looking for solutions like yours.",
  },
  twitter: {
    card: "summary_large_image",
    title: "WRRK - AI-Powered Lead Prospecting",
    description: "Find high-intent leads with AI-powered prospecting. Discover decision-makers actively looking for solutions like yours.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
