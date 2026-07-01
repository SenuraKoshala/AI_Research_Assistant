export const API = "http://127.0.0.1:8000";

/**
 * POST to an SSE (Server-Sent Events) endpoint and call `onEvent` for every
 * event the server pushes. axios can't read a streaming body in the browser,
 * so we use fetch + a ReadableStream reader instead.
 *
 * The server sends messages shaped like:  `data: {json}\n\n`
 * We buffer the raw text, split on the blank-line separator ("\n\n"),
 * parse each complete `data:` line as JSON, and hand it to onEvent.
 *
 * @param {string} path      e.g. "/chat/stream"
 * @param {object} body      request payload (sent as JSON)
 * @param {(evt: object) => void} onEvent  called once per parsed event
 */
export async function streamSSE(path, body, onEvent) {
  const res = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok || !res.body) {
    throw new Error(`Request to ${path} failed: ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // Everything up to the last "\n\n" is complete; keep the remainder.
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";

    for (const part of parts) {
      const dataLine = part
        .split("\n")
        .find((line) => line.startsWith("data:"));
      if (!dataLine) continue;

      const json = dataLine.slice(5).trim();
      if (!json) continue;

      try {
        onEvent(JSON.parse(json));
      } catch (err) {
        console.error("Failed to parse SSE event:", json, err);
      }
    }
  }
}