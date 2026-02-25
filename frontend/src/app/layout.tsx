import type { Metadata } from "next";
import { Geist_Mono } from "next/font/google";
import { GeistPixelSquare } from "geist/font/pixel";
import "./globals.css";

const mono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "limes — anonymous ephemeral broadcast network",
  description: "decentralized terminal chat. messages vanish after 24 minutes. proof-of-work. $LIME token rewards. no servers, no accounts, no history.",
  metadataBase: new URL("https://lime.sh"),
  openGraph: {
    title: "limes",
    description: "anonymous ephemeral broadcast network. messages vanish after 24 minutes.",
    url: "https://lime.sh",
    siteName: "limes",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "limes",
    description: "anonymous ephemeral broadcast network. messages vanish after 24 minutes.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${mono.variable} ${GeistPixelSquare.variable} antialiased`}>{children}</body>
    </html>
  );
}
