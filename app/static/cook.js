const dialog = document.getElementById("cook-dialog");
const form = document.getElementById("cook-form");
const title = document.getElementById("cook-title");
const utensilEl = document.getElementById("cook-utensil");
const qtyInput = document.getElementById("cook-qty");
const slotsEl = document.getElementById("cook-slots");
const errorEl = document.getElementById("cook-error");
const confirmBtn = document.getElementById("cook-confirm");
const cancelBtn = document.getElementById("cook-cancel");

let preview = null;

function setError(message) {
  errorEl.hidden = !message;
  errorEl.textContent = message || "";
}

function assignedFor(slotIndex) {
  const inputs = slotsEl.querySelectorAll(`[data-slot="${slotIndex}"]`);
  let total = 0;
  inputs.forEach((input) => {
    total += Number(input.value) || 0;
  });
  return total;
}

function remainingFor(itemId, exceptSlot) {
  const option = preview.slots.flatMap((slot) => slot.options).find((row) => row.id === itemId);
  let left = option ? option.have : 0;
  slotsEl.querySelectorAll(`input[data-item="${itemId}"]`).forEach((input) => {
    const slotIndex = Number(input.dataset.slot);
    if (slotIndex !== exceptSlot) {
      left -= Number(input.value) || 0;
    }
  });
  return left;
}

function neededFor(slot) {
  return slot.quantity * (Number(qtyInput.value) || 1);
}

function refreshSlots() {
  if (!preview) return;
  preview.slots.forEach((slot, slotIndex) => {
    const need = neededFor(slot);
    const assigned = assignedFor(slotIndex);
    const header = slotsEl.querySelector(`[data-slot-head="${slotIndex}"]`);
    if (header) {
      header.textContent = `${assigned} / ${need}`;
      header.className = assigned === need ? "ok" : "bad";
    }
    slotsEl.querySelectorAll(`[data-slot="${slotIndex}"]`).forEach((input) => {
      const left = remainingFor(input.dataset.item, slotIndex);
      input.max = String(Math.max(0, left));
      const current = Number(input.value) || 0;
      if (current > left) input.value = String(Math.max(0, left));
    });
  });
  const qty = Number(qtyInput.value) || 1;
  const okQty = qty >= 1 && qty <= preview.max_cookable;
  const okSlots = preview.slots.every((slot, i) => assignedFor(i) === neededFor(slot));
  confirmBtn.disabled = !(okQty && okSlots);
}

function prefill() {
  slotsEl.querySelectorAll("input[data-item]").forEach((input) => {
    input.value = "0";
  });
  preview.slots.forEach((slot, slotIndex) => {
    const need = neededFor(slot);
    const covering = slot.options.filter((opt) => opt.have >= need);
    if (covering.length === 1 && slot.options.length >= 1) {
      const only = covering[0];
      const input = slotsEl.querySelector(`[data-slot="${slotIndex}"][data-item="${only.id}"]`);
      if (input) input.value = String(need);
    } else if (slot.options.length === 1 && slot.options[0].have >= need) {
      const input = slotsEl.querySelector(`[data-slot="${slotIndex}"][data-item="${slot.options[0].id}"]`);
      if (input) input.value = String(need);
    }
  });
  refreshSlots();
}

function renderSlots() {
  slotsEl.innerHTML = "";
  preview.slots.forEach((slot, slotIndex) => {
    const block = document.createElement("div");
    block.className = "slot-block";
    const head = document.createElement("header");
    head.innerHTML = `<strong>${slot.display}</strong><span data-slot-head="${slotIndex}"></span>`;
    block.appendChild(head);
    slot.options.forEach((opt) => {
      const row = document.createElement("label");
      row.className = "slot-row";
      row.innerHTML = `<span>${opt.name} <span class="muted">(have ${opt.have})</span></span>`;
      const input = document.createElement("input");
      input.type = "number";
      input.min = "0";
      input.value = "0";
      input.dataset.slot = String(slotIndex);
      input.dataset.item = opt.id;
      input.addEventListener("input", refreshSlots);
      row.appendChild(input);
      block.appendChild(row);
    });
    if (!slot.options.length) {
      const empty = document.createElement("p");
      empty.className = "muted";
      empty.textContent = "No matching items in inventory.";
      block.appendChild(empty);
    }
    slotsEl.appendChild(block);
  });
  prefill();
}

function collectSlots() {
  return preview.slots.map((slot, slotIndex) => {
    const alloc = {};
    slotsEl.querySelectorAll(`[data-slot="${slotIndex}"]`).forEach((input) => {
      const qty = Number(input.value) || 0;
      if (qty > 0) alloc[input.dataset.item] = qty;
    });
    return alloc;
  });
}

async function openCook(recipeId) {
  setError("");
  const res = await fetch(`/api/recipes/${recipeId}/cook`);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    showFlash(data.detail || "Cannot cook this recipe.", true);
    return;
  }
  preview = data;
  title.textContent = `Cook ${data.name}`;
  utensilEl.textContent = data.utensil ? `Uses ${data.utensil}` : "";
  qtyInput.max = String(data.max_cookable);
  qtyInput.value = "1";
  renderSlots();
  dialog.showModal();
}

qtyInput.addEventListener("input", () => {
  if (!preview) return;
  const qty = Number(qtyInput.value) || 1;
  if (qty > preview.max_cookable) qtyInput.value = String(preview.max_cookable);
  prefill();
});

cancelBtn.addEventListener("click", () => dialog.close());

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!preview) return;
  setError("");
  try {
    const data = await postJson(`/api/recipes/${preview.id}/cook`, {
      quantity: Number(qtyInput.value) || 1,
      slots: collectSlots(),
    });
    const extra = data.produced ? ` Added ${data.quantity} ${data.produced} to inventory.` : "";
    sessionStorage.setItem("flash", `Cooked ${data.quantity}× ${data.name}.${extra}`);
    dialog.close();
    window.location.reload();
  } catch (err) {
    setError(err.message);
  }
});

document.querySelectorAll("[data-cook]").forEach((btn) => {
  btn.addEventListener("click", () => openCook(btn.dataset.cook));
});
