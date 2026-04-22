import { type NextRequest, NextResponse } from "next/server";
import { updateSession } from "@/lib/supabase/middleware";

export async function middleware(request: NextRequest) {
  const { user, response } = await updateSession(request);

  // Auth gate temporarily disabled: /chat and /account are reachable without a session.
  // Previous behavior (restore if you want mandatory login for these routes):
  // if (
  //   request.nextUrl.pathname.startsWith("/chat") ||
  //   request.nextUrl.pathname.startsWith("/account")
  // ) {
  //   if (!user) {
  //     return NextResponse.redirect(new URL("/login", request.url));
  //   }
  // }

  // Auth pages: redirect to chat if already logged in
  if (
    request.nextUrl.pathname === "/login" ||
    request.nextUrl.pathname === "/signup"
  ) {
    if (user) {
      return NextResponse.redirect(new URL("/chat", request.url));
    }
  }

  return response;
}

export const config = {
  matcher: [
    // Match all paths except static files and Next.js internals
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
