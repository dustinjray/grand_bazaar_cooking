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
