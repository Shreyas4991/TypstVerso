"use strict";
const pages = JSON.parse(document.getElementById("document-data").textContent);
const container = document.getElementById("pages");
const links = document.getElementById("page-links");
for (const [index, page] of pages.entries()) {
  const section = document.createElement("section");
  section.className = "page";
  section.id = "page-" + (index + 1);
  section.setAttribute("aria-label", "Page " + (index + 1));
  section.style.aspectRatio = String(page.width / page.height);
  leanTooltips.mount(section, page);
  container.append(section);
  if (links) {
    const item = document.createElement("li");
    const link = document.createElement("a");
    link.href = "#" + section.id;
    link.textContent = "Page " + (index + 1);
    item.append(link);
    links.append(item);
  }
}
document.getElementById("page-count").textContent = pages.length + (pages.length === 1 ? " page" : " pages");
// Pages are created dynamically, so resolve a saved fragment after mounting them.
const target = document.getElementById(location.hash.slice(1));
if (target) target.scrollIntoView();
