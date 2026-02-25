import { NextRequest, NextResponse } from "next/server";

const SCANNER_HOSTS = ["limescan.xyz", "www.limescan.xyz"];

export function proxy(request: NextRequest) {
  const host = request.headers.get("host")?.split(":")[0] ?? "";

  if (SCANNER_HOSTS.includes(host)) {
    const { pathname } = request.nextUrl;

    if (pathname === "/") {
      return NextResponse.rewrite(new URL("/scan", request.url));
    }

    if (pathname === "/scan") {
      return NextResponse.next();
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next|api|favicon|icon|opengraph|twitter|.*\\..*).*)"],
};
