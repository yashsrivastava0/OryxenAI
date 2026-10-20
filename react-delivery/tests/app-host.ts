import {
  AppBridge,
  PostMessageTransport,
} from "@modelcontextprotocol/ext-apps/app-bridge";

const iframe = document.querySelector<HTMLIFrameElement>("iframe")!;
const bridge = new AppBridge(
  null,
  { name: "OryxenAI test host", version: "1.0.0" },
  { serverTools: {} },
);
bridge.oncalltool = async (args) => {
  const response = await fetch("/app-tool", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(args),
  });
  return response.json();
};
bridge.oninitialized = async () => {
  const manifest = await (await fetch("/app-manifest")).json();
  await bridge.sendToolInput({ arguments: { share_link: "test-share-link" } });
  await bridge.sendToolResult({
    content: [],
    structuredContent: { preview: "available" },
    _meta: { share_link: "test-share-link", manifest },
  });
};
await bridge.connect(
  new PostMessageTransport(iframe.contentWindow!, iframe.contentWindow!),
);
iframe.src = "/viewer";
