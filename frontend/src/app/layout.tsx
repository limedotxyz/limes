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
    title: "limes — anonymous ephemeral broadcast network for the terminal",
    description: "decentralized P2P chat where messages vanish after 24 minutes. proof-of-work spam prevention, $LIME token rewards for relay operators, end-to-end encrypted. no servers, no accounts, no history.",
    url: "https://lime.sh",
    siteName: "limes",
    type: "website",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "limes — anonymous ephemeral broadcast network",
        type: "image/png",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "limes — anonymous ephemeral broadcast network for the terminal",
    description: "decentralized P2P chat where messages vanish after 24 minutes. proof-of-work spam prevention, $LIME token rewards for relay operators, end-to-end encrypted.",
    images: ["/og-image.png"],
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
