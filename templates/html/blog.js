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
const pages = JSON.parse(document.getElementById("document-data").textContent);
const container = document.getElementById("pages");
const contents = document.getElementById("table-of-contents");
const headings = [];
for (const [index, page] of pages.entries()) {
  const section = document.createElement("section");
  section.className = "page";
  section.id = "page-" + (index + 1);
  section.setAttribute("aria-label", "Blog content");
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
  const posts = headings.filter(heading => heading.level === 1);
  for (const post of posts) {
    const item = document.createElement("li");
    const link = document.createElement("a");
    link.href = "#" + post.id;
    link.textContent = post.title;
    item.append(link);
    contents.append(item);
  }
  contents.closest("nav").hidden = !posts.length;
}
// Pages are created dynamically, so resolve a saved fragment after mounting them.
const target = document.getElementById(location.hash.slice(1));
if (target) target.scrollIntoView();
