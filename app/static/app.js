async function postJson(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = data.detail || res.statusText;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

function showFlash(message, isError) {
  const el = document.getElementById("flash");
  if (!el) return;
  el.textContent = message;
  el.hidden = false;
  el.classList.toggle("error-flash", Boolean(isError));
  window.setTimeout(() => {
    el.hidden = true;
  }, 4000);
}

const pendingFlash = sessionStorage.getItem("flash");
if (pendingFlash) {
  sessionStorage.removeItem("flash");
  showFlash(pendingFlash, false);
}
