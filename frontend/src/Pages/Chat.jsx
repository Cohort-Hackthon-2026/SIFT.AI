import MainLayout from "../components/layout/MainLayout";

import ChatWindow from "../components/chat/ChatWindow";

import PromptInput from "../components/composer/PromptInput";

import UploadDrawer from "../components/upload/UploadDrawer";

import CitationDrawer from "../components/chat/CitationDrawer";

function Chat() {
  return (
    <MainLayout>

      <ChatWindow />

      <PromptInput />

      <UploadDrawer />

      <CitationDrawer />

    </MainLayout>
  );
}

export default Chat;