const expireFilter = document.getElementById("expire-filter");
if (expireFilter) {
  expireFilter.addEventListener("input", () => {
    const q = expireFilter.value.trim().toLowerCase();
    document.querySelectorAll(".expire-item").forEach((row) => {
      const name = row.dataset.name || "";
      row.classList.toggle("hidden", Boolean(q) && !name.includes(q));
    });
  });
}

const slotDialog = document.getElementById("slot-dialog");
const slotTitle = document.getElementById("slot-dialog-title");
const slotNeed = document.getElementById("slot-dialog-need");
const slotList = document.getElementById("slot-dialog-list");

function parseSlotItems(raw) {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function openSlotDialog(btn) {
  if (!slotDialog || !slotTitle || !slotNeed || !slotList) return;
  const display = btn.dataset.display || "Ingredient";
  const qty = btn.dataset.qty || "1";
  const items = parseSlotItems(btn.dataset.items);
  items.sort((a, b) => {
    const owned = Number((Number(b.have) || 0) > 0) - Number((Number(a.have) || 0) > 0);
    if (owned) return owned;
    return String(a.name || "").localeCompare(String(b.name || ""), undefined, { sensitivity: "base" });
  });
  slotTitle.textContent = display;
  const noun = items.length === 1 ? "item" : "items";
  slotNeed.textContent = `Need ${qty} · ${items.length} ${noun} can fill this slot`;
  slotList.replaceChildren();
  if (!items.length) {
    const empty = document.createElement("li");
    empty.className = "unowned";
    empty.textContent = "No known items fill this slot.";
    slotList.appendChild(empty);
  } else {
    items.forEach((item) => {
      const li = document.createElement("li");
      const have = Number(item.have) || 0;
      li.className = have > 0 ? "owned" : "unowned";
      const name = document.createElement("span");
      name.textContent = item.name || item.id || "";
      li.appendChild(name);
      if (have > 0) {
        const count = document.createElement("span");
        count.className = "muted";
        count.textContent = `×${have}`;
        li.appendChild(count);
      }
      slotList.appendChild(li);
    });
  }
  slotDialog.showModal();
}

document.querySelectorAll(".slot-btn").forEach((btn) => {
  btn.addEventListener("click", () => openSlotDialog(btn));
});

const recipeList = document.querySelector(".recipe-list");
const ownedOnly = recipeList?.dataset.ownedOnly === "true";

function showOwnedEmpty() {
  if (!recipeList || recipeList.querySelector(".recipe-card")) return;
  const empty = document.createElement("p");
  empty.className = "empty";
  empty.textContent =
    "No owned recipes yet. Uncheck Owned only to browse the catalog and tick recipes you've found.";
  recipeList.replaceWith(empty);
}

document.querySelectorAll("[data-recipe-owned]").forEach((box) => {
  box.addEventListener("change", async () => {
    try {
      await postJson(`/api/recipes/${box.dataset.recipeOwned}/owned`, { owned: box.checked });
      if (ownedOnly && !box.checked) {
        box.closest(".recipe-card")?.remove();
        showOwnedEmpty();
      }
    } catch (err) {
      box.checked = !box.checked;
      showFlash(err.message, true);
    }
  });
});
