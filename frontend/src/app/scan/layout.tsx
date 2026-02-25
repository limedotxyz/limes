import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "limescan — live network explorer",
  description: "real-time block explorer for the limes network. view live messages, proof-of-work hashes, active authors, mining activity, and relay stats. all messages are ephemeral and vanish after 24 minutes.",
  metadataBase: new URL("https://limescan.xyz"),
  openGraph: {
    title: "limescan — live explorer for the limes broadcast network",
    description: "real-time block explorer for limes. view live messages, proof-of-work hashes, active authors, and mining activity. all messages are ephemeral and vanish after 24 minutes.",
    url: "https://limescan.xyz",
    siteName: "limescan",
    type: "website",
    images: [
      {
        url: "https://lime.sh/og-image.png",
        width: 1200,
        height: 630,
        alt: "limescan — live network explorer",
        type: "image/png",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "limescan — live explorer for the limes broadcast network",
    description: "real-time block explorer for limes. view live messages, proof-of-work hashes, active authors, and mining activity. all messages vanish after 24 minutes.",
    images: ["https://lime.sh/og-image.png"],
  },
};

export default function ScanLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return children;
}
