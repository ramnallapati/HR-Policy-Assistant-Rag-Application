const messages = document.getElementById("messages");
const form = document.getElementById("chatForm");
const input = document.getElementById("question");
const sendBtn = document.getElementById("sendBtn");

function addMessage(role, text, sources = []) {
  const row = document.createElement("div");
  row.className = `message ${role}`;
  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = role === "assistant" ? "P" : "Y";
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  const paragraph = document.createElement("p");
  paragraph.textContent = text;
  bubble.appendChild(paragraph);
  if (sources.length) {
    const details = document.createElement("details");
    details.className = "sources";
    const summary = document.createElement("summary");
    summary.textContent = `Sources used (${sources.length})`;
    details.appendChild(summary);
    sources.forEach((source) => {
      const card = document.createElement("div");
      card.className = "source-card";
      const title = document.createElement("b");
      title.textContent = `${source.document} · Chunk ${source.chunk}`;
      const excerpt = document.createElement("p");
      excerpt.textContent = source.excerpt;
      const distance = document.createElement("small");
      distance.textContent = `Vector distance: ${source.distance} (lower is closer)`;
      card.append(title, excerpt, distance);
      details.appendChild(card);
    });
    bubble.appendChild(details);
  }
  row.append(avatar, bubble);
  messages.appendChild(row);
  messages.scrollTop = messages.scrollHeight;
}

async function sendQuestion(question) {
  if (!question.trim()) return;
  addMessage("user", question.trim());
  input.value = "";
  sendBtn.disabled = true;
  sendBtn.textContent = "…";
  const thinking = document.createElement("div");
  thinking.className = "typing";
  thinking.textContent = "Searching policy documents…";
  messages.appendChild(thinking);
  messages.scrollTop = messages.scrollHeight;
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({question: question.trim()})
    });
    const data = await response.json();
    thinking.remove();
    if (!response.ok) throw new Error(data.error || "Request failed.");
    addMessage("assistant", data.answer, data.sources || []);
  } catch (error) {
    thinking.remove();
    addMessage("assistant", `Sorry, I couldn't complete that request. ${error.message}`);
  } finally {
    sendBtn.disabled = false;
    sendBtn.textContent = "↑";
    input.focus();
  }
}

form?.addEventListener("submit", (event) => {
  event.preventDefault();
  sendQuestion(input.value);
});
input?.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});
document.querySelectorAll("[data-prompt]").forEach(button => {
  button.addEventListener("click", () => sendQuestion(button.dataset.prompt));
});
document.getElementById("clearChat")?.addEventListener("click", () => {
  messages.replaceChildren();
  addMessage("assistant", "Chat cleared. What HR policy would you like to explore?");
});
async function loadDocuments() {
  const list = document.getElementById("docList");
  if (!list) return;
  try {
    const response = await fetch("/api/documents");
    const data = await response.json();
    list.replaceChildren();
    if (!data.documents.length) {
      const empty = document.createElement("p");
      empty.className = "muted";
      empty.textContent = "No policy documents indexed yet.";
      list.appendChild(empty);
      return;
    }
    data.documents.forEach(doc => {
      const item = document.createElement("div");
      item.className = "doc-item";
      const icon = document.createElement("span");
      icon.className = "file-icon";
      icon.textContent = "DOC";
      const info = document.createElement("div");
      const name = document.createElement("b");
      name.textContent = doc.name;
      const chunks = document.createElement("small");
      chunks.textContent = `${doc.chunks} chunks`;
      info.append(name, chunks);
      item.append(icon, info);
      list.appendChild(item);
    });
  } catch {
    list.textContent = "Could not load document list.";
  }
}
loadDocuments();
