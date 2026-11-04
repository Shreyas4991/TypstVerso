/*
Copyright 2026 Shreyas Srinivas

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

"use strict";
const leanTooltips = (() => {
  const tooltip = document.getElementById("tooltip");
  let pinned = false, active = null, activeRegion = null, hoveringTooltip = false, hideTimer = null;
  function cancelHide() {
    clearTimeout(hideTimer);
    hideTimer = null;
  }
  function hideSoon() {
    if (pinned) return;
    cancelHide();
    hideTimer = setTimeout(() => {
      if (!pinned && !hoveringTooltip && !tooltip.matches(":focus-within")) close();
    }, 200);
  }
  function close() {
    cancelHide();
    pinned = false;
    hoveringTooltip = false;
    tooltip.hidden = true;
    if (active) {
      active.classList.remove("active");
      active.removeAttribute("aria-describedby");
    }
    active = null;
    activeRegion = null;
  }
  function show(button, region) {
    if (pinned) return;
    if (active === button) cancelHide();
    else close();
    active = button;
    activeRegion = region;
    button.classList.add("active");
    button.setAttribute("aria-describedby", "tooltip");
    tooltip.textContent = region.tooltip;
    tooltip.dataset.pinned = "false";
    tooltip.style.maxHeight = "";
    tooltip.style.left = "12px";
    tooltip.style.top = "12px";
    tooltip.hidden = false;
    const rect = button.getBoundingClientRect();
    const width = tooltip.offsetWidth, height = tooltip.offsetHeight;
    tooltip.style.left = Math.max(12, Math.min(rect.left, innerWidth - width - 12)) + "px";
    const below = rect.bottom + 10;
    const belowSpace = innerHeight - below - 12;
    const aboveSpace = rect.top - 22;
    const useBelow = belowSpace >= Math.min(height, 80) || belowSpace >= aboveSpace;
    const available = Math.max(0, useBelow ? belowSpace : aboveSpace);
    const fittedHeight = Math.min(height, available);
    tooltip.style.maxHeight = fittedHeight + "px";
    // Read the final height after limiting it, including padding and borders.
    // Clamping an above-text popup to the viewport top can cover its trigger.
    tooltip.style.top = (useBelow ? below : rect.top - tooltip.offsetHeight - 10) + "px";
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
      button.addEventListener("pointerleave", hideSoon);
      button.addEventListener("focus", () => show(button, region));
      button.addEventListener("blur", hideSoon);
      button.addEventListener("click", event => {
        event.stopPropagation();
        if (pinned && active === button) { close(); return; }
        close();
        show(button, region);
        pinned = true;
        tooltip.dataset.pinned = "true";
      });
      container.append(button);
    }
  }
  tooltip.tabIndex = 0;
  tooltip.addEventListener("pointerenter", () => { hoveringTooltip = true; cancelHide(); });
  tooltip.addEventListener("pointerleave", () => { hoveringTooltip = false; hideSoon(); });
  tooltip.addEventListener("focus", cancelHide);
  tooltip.addEventListener("blur", hideSoon);
  tooltip.addEventListener("wheel", event => {
    if (event.ctrlKey || !event.deltaY || tooltip.scrollHeight <= tooltip.clientHeight) return;
    // Keep docstring scrolling inside the popup, even in a scrolling reader.
    const unit = event.deltaMode === 1 ? parseFloat(getComputedStyle(tooltip).lineHeight)
      : event.deltaMode === 2 ? tooltip.clientHeight : 1;
    event.preventDefault();
    hoveringTooltip = true;
    cancelHide();
    tooltip.scrollTop += event.deltaY * unit;
  }, {passive: false});
  addEventListener("keydown", event => { if (event.key === "Escape") close(); });
  addEventListener("click", event => { if (!tooltip.contains(event.target)) close(); });
  addEventListener("resize", close);
  addEventListener("scroll", () => {
    if (pinned || hoveringTooltip || tooltip.matches(":focus-within")) return;
    if (active && active.matches(":hover")) show(active, activeRegion);
    else close();
  }, {passive: true});
  return {close, mount};
})();
