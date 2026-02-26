import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "limes web client — browser terminal",
  description:
    "access the limes anonymous broadcast network directly from your browser. no download required.",
};

export default function WebLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return children;
}
