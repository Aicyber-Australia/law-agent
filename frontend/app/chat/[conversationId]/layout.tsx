import { CopilotKit } from "@copilotkit/react-core";

export default function ConversationLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: { conversationId: string };
}) {
  return (
    <CopilotKit
      runtimeUrl="/api/copilotkit"
      agent="auslaw_agent"
      threadId={params.conversationId}
    >
      {children}
    </CopilotKit>
  );
}
