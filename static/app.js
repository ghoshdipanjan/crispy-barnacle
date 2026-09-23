const listsElement = document.querySelector("#lists");
const messageElement = document.querySelector("#message");
const listForm = document.querySelector("#new-list-form");

async function api(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.error || "Something went wrong");
  }
  return response.status === 204 ? null : response.json();
}

function showMessage(message = "", isError = false) {
  messageElement.textContent = message;
  messageElement.classList.toggle("error", isError);
}

function createItemElement(listId, item) {
  const row = document.createElement("li");
  row.className = item.completed ? "completed" : "";

  const label = document.createElement("label");
  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.checked = item.completed;
  checkbox.addEventListener("change", async () => {
    try {
      await api(`/api/lists/${listId}/items/${item.id}`, {
        method: "PATCH",
        body: JSON.stringify({ completed: checkbox.checked }),
      });
      row.classList.toggle("completed", checkbox.checked);
    } catch (error) {
      checkbox.checked = !checkbox.checked;
      showMessage(error.message, true);
    }
  });

  const name = document.createElement("span");
  name.textContent = item.name;
  label.append(checkbox, name);

  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "icon-button";
  remove.textContent = "Remove";
  remove.addEventListener("click", async () => {
    try {
      await api(`/api/lists/${listId}/items/${item.id}`, { method: "DELETE" });
      row.remove();
    } catch (error) {
      showMessage(error.message, true);
    }
  });

  row.append(label, remove);
  return row;
}

function createListElement(list) {
  const card = document.createElement("article");
  card.className = "list-card";

  const heading = document.createElement("div");
  heading.className = "list-heading";
  const title = document.createElement("h2");
  title.textContent = list.name;
  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "icon-button";
  remove.textContent = "Delete list";
  remove.addEventListener("click", async () => {
    try {
      await api(`/api/lists/${list.id}`, { method: "DELETE" });
      card.remove();
      if (!listsElement.children.length) renderEmptyState();
    } catch (error) {
      showMessage(error.message, true);
    }
  });
  heading.append(title, remove);

  const items = document.createElement("ul");
  list.items.forEach((item) => items.append(createItemElement(list.id, item)));

  const form = document.createElement("form");
  form.className = "item-form";
  const input = document.createElement("input");
  input.maxLength = 200;
  input.placeholder = "Add an item";
  input.setAttribute("aria-label", `Add an item to ${list.name}`);
  input.required = true;
  const add = document.createElement("button");
  add.textContent = "Add";
  form.append(input, add);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const item = await api(`/api/lists/${list.id}/items`, {
        method: "POST",
        body: JSON.stringify({ name: input.value }),
      });
      items.append(createItemElement(list.id, item));
      input.value = "";
      showMessage();
    } catch (error) {
      showMessage(error.message, true);
    }
  });

  card.append(heading, items, form);
  return card;
}

function renderEmptyState() {
  const empty = document.createElement("p");
  empty.className = "empty";
  empty.textContent = "No lists yet. Create one to get started.";
  listsElement.replaceChildren(empty);
}

async function loadLists() {
  try {
    const lists = await api("/api/lists");
    if (!lists.length) {
      renderEmptyState();
      return;
    }
    listsElement.replaceChildren(...lists.map(createListElement));
  } catch (error) {
    showMessage(error.message, true);
  }
}

listForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = document.querySelector("#new-list-name");
  try {
    const list = await api("/api/lists", {
      method: "POST",
      body: JSON.stringify({ name: input.value }),
    });
    if (listsElement.querySelector(".empty")) listsElement.replaceChildren();
    listsElement.append(createListElement(list));
    input.value = "";
    showMessage();
  } catch (error) {
    showMessage(error.message, true);
  }
});

loadLists();
