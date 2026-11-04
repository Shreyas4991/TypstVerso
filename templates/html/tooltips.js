"use strict";
const leanTooltips = (() => {
  const tooltip = document.getElementById("tooltip");
  let pinned = false, active = null;
  function close() {
    pinned = false;
    tooltip.hidden = true;
    if (active) {
      active.classList.remove("active");
      active.removeAttribute("aria-describedby");
    }
    active = null;
  }
  function show(button, region) {
    if (pinned) return;
    close();
    active = button;
    button.classList.add("active");
    button.setAttribute("aria-describedby", "tooltip");
    tooltip.textContent = region.tooltip;
    tooltip.hidden = false;
    const rect = button.getBoundingClientRect();
    const width = tooltip.offsetWidth, height = tooltip.offsetHeight;
    tooltip.style.left = Math.max(12, Math.min(rect.left, innerWidth - width - 12)) + "px";
    const below = rect.bottom + 10;
    tooltip.style.top = Math.max(12, below + height < innerHeight - 12 ? below : rect.top - height - 10) + "px";
  }
  function mount(container, page) {
    container.innerHTML = page.svg;
    for (const region of page.regions) {
      const button = document.createElement("button");
      button.className = "hover";
      button.dataset.role = region.role;
      button.setAttribute("aria-label", region.role === "state" ? "Proof state: " + region.tooltip : region.tooltip);
      button.style.left = (100 * region.x / page.width) + "%";
      button.style.top = (100 * region.y / page.height) + "%";
      button.style.width = (100 * region.width / page.width) + "%";
      button.style.height = (100 * region.height / page.height) + "%";
      button.addEventListener("pointerenter", () => show(button, region));
      button.addEventListener("pointerleave", () => { if (!pinned) close(); });
      button.addEventListener("focus", () => show(button, region));
      button.addEventListener("blur", () => { if (!pinned) close(); });
      button.addEventListener("click", event => {
        event.stopPropagation();
        if (pinned && active === button) { close(); return; }
        close();
        show(button, region);
        pinned = true;
      });
      container.append(button);
    }
  }
  addEventListener("keydown", event => { if (event.key === "Escape") close(); });
  addEventListener("click", event => { if (!tooltip.contains(event.target)) close(); });
  addEventListener("resize", close);
  addEventListener("scroll", () => { if (!pinned) close(); }, {passive: true});
  return {close, mount};
})();
