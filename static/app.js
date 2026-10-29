"use strict";

(function () {
  const chatForm = document.getElementById("chat-form");
  const chatInput = document.getElementById("chat-input");
  const sendButton = document.getElementById("send-button");
  const messages = document.getElementById("messages");
  const prompts = document.getElementById("quick-prompts");
  const taskForm = document.getElementById("task-form");
  const taskInput = document.getElementById("task-input");
  const taskList = document.getElementById("task-list");
  const taskEmpty = document.getElementById("task-empty");
  const heading = document.getElementById("mode-heading");
  const description = document.getElementById("mode-description");
  const assistantName = document.getElementById("assistant-name");
  const hotelName = heading.textContent;
  const STORAGE_KEY = "aitaskflo-concierge-demo-tasks-v1";
  let mode = "hotel";
  let busy = false;
  let tasks = [];

  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
    if (Array.isArray(saved)) {
      tasks = saved.filter(function (item) {
        return item && typeof item.text === "string" && item.text.length <= 160 &&
          typeof item.done === "boolean" && typeof item.id === "string";
      }).slice(0, 100);
    }
  } catch (_) {
    // Private browsing and managed devices may block storage. The UI still works.
  }

  function persistTasks() {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks)); }
    catch (_) { /* Checklist remains usable for the current page. */ }
  }

  function renderTasks() {
    taskList.replaceChildren();
    taskEmpty.hidden = tasks.length > 0;
    tasks.forEach(function (item) {
      const li = document.createElement("li");
      if (item.done) li.className = "done";
      const label = document.createElement("label");
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.checked = item.done;
      checkbox.setAttribute("aria-label", "Complete " + item.text);
      checkbox.addEventListener("change", function () {
        item.done = checkbox.checked;
        persistTasks();
        renderTasks();
      });
      const span = document.createElement("span");
      span.className = "task-label";
      span.textContent = item.text;
      label.append(checkbox, span);
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "remove";
      remove.textContent = "×";
      remove.setAttribute("aria-label", "Remove " + item.text);
      remove.addEventListener("click", function () {
        tasks = tasks.filter(function (task) { return task.id !== item.id; });
        persistTasks();
        renderTasks();
      });
      li.append(label, remove);
      taskList.appendChild(li);
    });
  }

  function addTask(text) {
    const value = String(text || "").trim().slice(0, 160);
    if (!value || tasks.length >= 100) return false;
    tasks.unshift({ id: String(Date.now()) + "-" + String(Math.random()), text: value, done: false });
    persistTasks();
    renderTasks();
    return true;
  }

  function addMessage(text, role, action) {
    const wrapper = document.createElement("div");
    wrapper.className = "message " + role;
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = text;
    wrapper.appendChild(bubble);

    if (role === "assistant" && action && typeof action.text === "string") {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "action-button";
      if (action.type === "propose_task") {
        button.textContent = "＋ Add task to my checklist";
        button.addEventListener("click", function () {
          if (addTask(action.text)) {
            button.textContent = "✓ Added locally";
            button.disabled = true;
          } else {
            button.textContent = "Checklist full or task invalid";
          }
        });
        wrapper.appendChild(button);
      } else if (action.type === "draft_request") {
        button.textContent = "Copy request draft";
        button.addEventListener("click", async function () {
          const draft = "Service request (not submitted): " + action.text;
          try {
            if (!navigator.clipboard) throw new Error("Clipboard not supported");
            await navigator.clipboard.writeText(draft);
            button.textContent = "✓ Draft copied — contact the front desk";
          } catch (_) {
            button.textContent = "Select the text below and copy manually";
            addMessage(draft, "assistant");
          }
        });
        wrapper.appendChild(button);
      }
    }
    messages.appendChild(wrapper);
    messages.scrollTop = messages.scrollHeight;
  }

  function setPrompts(items) {
    prompts.replaceChildren();
    items.forEach(function (value) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.dataset.prompt = value;
      btn.textContent = value;
      btn.addEventListener("click", function () { send(value); });
      prompts.appendChild(btn);
    });
  }

  function setMode(next) {
    if (busy || next === mode) return;
    mode = next;
    document.querySelectorAll(".mode-button").forEach(function (button) {
      const selected = button.dataset.mode === mode;
      button.classList.toggle("active", selected);
      button.setAttribute("aria-pressed", String(selected));
    });
    messages.replaceChildren();
    if (mode === "hotel") {
      heading.textContent = hotelName;
      description.textContent = "Hospitality at your fingertips. Ask about your stay, amenities, or prepare a service request.";
      assistantName.textContent = "Hotel Concierge";
      addMessage("Welcome! Ask me about check-in, breakfast, parking, amenities, or a housekeeping request. All hotel details shown here are examples.", "assistant");
      setPrompts(["Check-in time", "Breakfast", "Hotel amenities", "Request extra towels"]);
    } else {
      heading.textContent = "Your day, made simpler.";
      description.textContent = "Plan your day, organize travel, and keep a personal checklist on this device.";
      assistantName.textContent = "Personal Assistant";
      addMessage("Hello! I can help you plan, pack, and prepare a private to-do list. Tasks are saved only in your browser.", "assistant");
      setPrompts(["Plan my day", "Packing checklist", "Remind me to pack my charger"]);
    }
    chatInput.focus();
  }

  async function send(raw) {
    const value = String(raw || "").trim();
    if (!value || busy || value.length > 1000) return;
    busy = true;
    sendButton.disabled = true;
    chatInput.value = "";
    addMessage(value, "user");
    const currentMode = mode;
    try {
      const result = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: value, mode: currentMode })
      });
      const payload = await result.json();
      if (!result.ok) throw new Error(payload.error || "The request failed.");
      addMessage(payload.reply, "assistant", payload.action);
      if (Array.isArray(payload.suggestions)) setPrompts(payload.suggestions.slice(0, 4));
    } catch (error) {
      addMessage("I couldn't respond just now. " + (error.message || "Try again."), "assistant");
    } finally {
      busy = false;
      sendButton.disabled = false;
      chatInput.focus();
    }
  }

  chatForm.addEventListener("submit", function (event) {
    event.preventDefault();
    send(chatInput.value);
  });
  taskForm.addEventListener("submit", function (event) {
    event.preventDefault();
    if (addTask(taskInput.value)) taskInput.value = "";
  });
  document.querySelectorAll(".mode-button").forEach(function (button) {
    button.addEventListener("click", function () { setMode(button.dataset.mode); });
  });
  setPrompts(["Check-in time", "Breakfast", "Hotel amenities", "Request extra towels"]);
  renderTasks();
})();
