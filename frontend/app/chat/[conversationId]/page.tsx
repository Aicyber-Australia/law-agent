import ChatPageClient from "./ChatPageClient";

export default function ConversationPage({
  params,
}: {
  params: { conversationId: string };
}) {
  return <ChatPageClient conversationId={params.conversationId} />;
}
