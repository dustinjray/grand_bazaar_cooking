document.querySelectorAll("[data-appliance]").forEach((box) => {
  box.addEventListener("change", async () => {
    try {
      await postJson(`/api/appliances/${box.dataset.appliance}`, { owned: box.checked });
    } catch (err) {
      box.checked = !box.checked;
      showFlash(err.message, true);
    }
  });
});

function parseCount(value) {
  return Math.max(0, Number.parseInt(value, 10) || 0);
}

function isDirty(row) {
  const input = row.querySelector("[data-count]");
  return parseCount(input.value) !== parseCount(row.dataset.saved);
}

function anyDirty() {
  return Array.from(document.querySelectorAll(".item-row")).some(isDirty);
}

function syncRow(row) {
  const input = row.querySelector("[data-count]");
  const saveBtn = row.querySelector("[data-save]");
  const count = parseCount(input.value);
  input.value = String(count);
  const dirty = count !== parseCount(row.dataset.saved);
  row.classList.toggle("dirty", dirty);
  saveBtn.disabled = !dirty;
}

async function commitRow(row) {
  const input = row.querySelector("[data-count]");
  const saveBtn = row.querySelector("[data-save]");
  const itemId = row.dataset.itemId;
  const count = parseCount(input.value);
  input.value = String(count);
  saveBtn.disabled = true;
  try {
    const data = await postJson(`/api/inventory/${itemId}`, { count });
    row.dataset.saved = String(data.count);
    input.value = String(data.count);
    syncRow(row);
  } catch (err) {
    showFlash(err.message, true);
    syncRow(row);
  }
}

document.querySelectorAll(".item-row").forEach((row) => {
  const input = row.querySelector("[data-count]");
  row.querySelectorAll("[data-delta]").forEach((btn) => {
    btn.addEventListener("click", () => {
      input.value = String(parseCount(input.value) + Number(btn.dataset.delta));
      syncRow(row);
    });
  });
  input.addEventListener("input", () => syncRow(row));
  input.addEventListener("change", () => syncRow(row));
  row.querySelector("[data-save]").addEventListener("click", () => commitRow(row));
});

window.addEventListener("beforeunload", (event) => {
  if (!anyDirty()) return;
  event.preventDefault();
  event.returnValue = "";
});

document.querySelector(".filters")?.addEventListener("submit", (event) => {
  if (!anyDirty()) return;
  if (!window.confirm("You have unsaved inventory changes. Search anyway and discard them?")) {
    event.preventDefault();
  }
});
