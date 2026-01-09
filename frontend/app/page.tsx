"use client";

import { CopilotSidebar } from "@copilotkit/react-ui";

export default function Home() {
  return (
    <div className="flex h-screen bg-slate-50">
      {/* Left Side: Mock Document Viewer */}
      <div className="w-1/2 p-10 border-r border-slate-200 flex flex-col justify-center items-center">
        <div className="bg-white p-8 shadow-lg rounded-lg max-w-md w-full h-[600px] border">
          <h2 className="text-xl font-bold mb-4 text-slate-800">
            Uploaded Document
          </h2>
          <div className="bg-slate-100 p-4 rounded text-sm text-slate-500 h-full font-mono overflow-auto">
            [PDF Viewer Placeholder]
            <br />
            <br />
            USER CONTRACT:
            <br />
            &quot;The landlord reserves the right to increase rent every 3
            months...&quot;
          </div>
        </div>
      </div>

      {/* Right Side: Copilot Sidebar */}
      <div className="w-1/2 relative">
        <CopilotSidebar
          defaultOpen={true}
          instructions="You are AusLaw AI. Always cite sources."
          labels={{
            title: "AusLaw AI",
            initial:
              "Hello. I can analyze your case based on Victorian Tenancy Law.",
          }}
        />
      </div>
    </div>
  );
}
