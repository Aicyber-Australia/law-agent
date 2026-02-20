/**
 * AustLII Proxy Route
 *
 * Proxies requests to AustLII (Australian Legal Information Institute) because
 * AustLII blocks connections from our DigitalOcean backend. Vercel's network
 * is not blocked, so we route through here.
 *
 * Two actions:
 * - "search": proxy search queries to AustLII's search endpoint
 * - "fetch": fetch content from a specific AustLII page URL
 *
 * Secured with a shared secret in x-proxy-secret header.
 */

import { NextRequest, NextResponse } from "next/server";

const AUSTLII_SEARCH_URL =
  "https://www.austlii.edu.au/cgi-bin/sinosrch.cgi";
const ALLOWED_HOSTS = ["www.austlii.edu.au", "austlii.edu.au"];
const PROXY_SECRET = process.env.AUSTLII_PROXY_SECRET;

interface SearchRequestBody {
  action: "search";
  params: Record<string, string>;
}

interface FetchRequestBody {
  action: "fetch";
  url: string;
}

type RequestBody = SearchRequestBody | FetchRequestBody;

function isAustliiUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return (
      (parsed.protocol === "http:" || parsed.protocol === "https:") &&
      ALLOWED_HOSTS.includes(parsed.hostname)
    );
  } catch {
    return false;
  }
}

export async function POST(req: NextRequest) {
  // Verify shared secret
  if (!PROXY_SECRET) {
    return NextResponse.json(
      { error: "Proxy not configured" },
      { status: 500 }
    );
  }

  const secret = req.headers.get("x-proxy-secret");
  if (secret !== PROXY_SECRET) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  let body: RequestBody;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  try {
    if (body.action === "search") {
      // Proxy search request to AustLII
      const params = new URLSearchParams(body.params);
      const url = `${AUSTLII_SEARCH_URL}?${params.toString()}`;

      const response = await fetch(url, {
        headers: {
          "User-Agent": "AusLawAI/1.0 (legal research tool)",
          Referer: "https://www.austlii.edu.au/forms/search1.html",
        },
        signal: AbortSignal.timeout(30000),
      });

      const html = await response.text();
      return NextResponse.json({ html, status: response.status });
    }

    if (body.action === "fetch") {
      // SSRF protection: only allow AustLII URLs
      if (!isAustliiUrl(body.url)) {
        return NextResponse.json(
          { error: "URL not allowed" },
          { status: 403 }
        );
      }

      const response = await fetch(body.url, {
        headers: {
          "User-Agent": "AusLawAI/1.0 (legal research tool)",
        },
        redirect: "follow",
        signal: AbortSignal.timeout(30000),
      });

      // Verify final URL after redirects is still on AustLII
      const finalUrl = new URL(response.url);
      if (!ALLOWED_HOSTS.includes(finalUrl.hostname)) {
        return NextResponse.json(
          { error: "Redirect to non-AustLII host blocked" },
          { status: 403 }
        );
      }

      const html = await response.text();
      return NextResponse.json({ html, status: response.status });
    }

    return NextResponse.json({ error: "Invalid action" }, { status: 400 });
  } catch (e) {
    const message = e instanceof Error ? e.message : "Unknown error";
    return NextResponse.json(
      { error: `Proxy error: ${message}` },
      { status: 502 }
    );
  }
}
