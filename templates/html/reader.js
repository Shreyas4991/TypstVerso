"use strict";
const pages = JSON.parse(document.getElementById("document-data").textContent);
const container = document.getElementById("pages");
const contents = document.getElementById("table-of-contents");
const headings = [];
for (const [index, page] of pages.entries()) {
  const section = document.createElement("section");
  section.className = "page";
  section.id = "page-" + (index + 1);
  section.setAttribute("aria-label", "Page " + (index + 1));
  section.style.aspectRatio = String(page.width / page.height);
  leanTooltips.mount(section, page);
  container.append(section);
  for (const heading of page.headings || []) {
    const anchor = document.createElement("span");
    anchor.id = heading.id;
    anchor.className = "heading-anchor";
    anchor.style.position = "absolute";
    anchor.style.top = (100 * heading.y / page.height) + "%";
    anchor.style.left = "0";
    anchor.style.scrollMarginTop = "24px";
    anchor.setAttribute("aria-hidden", "true");
    section.append(anchor);
    headings.push(heading);
  }
}
if (contents) {
  const parents = [];
  for (const heading of headings) {
    while (parents.length && parents[parents.length - 1].level >= heading.level) parents.pop();
    let list = contents;
    if (parents.length) {
      const parent = parents[parents.length - 1].item;
      list = parent.querySelector(":scope > ol");
      if (!list) { list = document.createElement("ol"); parent.append(list); }
    }
    const item = document.createElement("li");
    const link = document.createElement("a");
    link.href = "#" + heading.id;
    link.textContent = heading.title;
    item.append(link);
    list.append(item);
    parents.push({level: heading.level, item});
  }
  contents.closest("nav").hidden = !headings.length;
}
document.getElementById("page-count").textContent = pages.length + (pages.length === 1 ? " page" : " pages");
// Pages are created dynamically, so resolve a saved fragment after mounting them.
const target = document.getElementById(location.hash.slice(1));
if (target) target.scrollIntoView();
