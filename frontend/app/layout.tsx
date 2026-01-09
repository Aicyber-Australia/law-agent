import type { Metadata } from "next";
import { CopilotKit } from "@copilotkit/react-core";
import "@copilotkit/react-ui/styles.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "AusLaw AI",
  description: "Australian Legal Assistant powered by AI",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        {/* Connect via Next.js API route to Python backend */}
        <CopilotKit
          runtimeUrl="/api/copilotkit"
          agent="auslaw_agent"
        >
          {children}
        </CopilotKit>
      </body>
    </html>
  );
}
