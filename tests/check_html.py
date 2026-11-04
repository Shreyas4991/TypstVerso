"""Optional browser smoke check: install Playwright and Google Chrome first."""
import argparse
from pathlib import Path

from playwright.sync_api import TimeoutError as BrowserTimeout, expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def check_hover_and_scroll(page, url, kind):
    # The slide samples exercise quote, state, and command separately. Reader
    # samples exercise command output in their own layouts. Use a long docstring
    # and short viewport to reproduce the previous overlap/hover feedback loop.
    cases = [0, 2, 3] if kind == "slides" else [None]
    for index in cases:
        page.set_viewport_size({"width": 1280, "height": 300})
        page.goto(url + ("#" + str(index + 1) if index is not None else ""))
        selector = page.evaluate("""({index, kind}) => {
          const data = JSON.parse(document.getElementById("document-data").textContent);
          let number = index;
          if (number === null) number = data.findLastIndex(p =>
            p.regions.some(r => r.tooltip.includes("Demo.identity_pair")));
          const source = data[number];
          const region = index === null
            ? source.regions.findLastIndex(r => r.tooltip.includes("Demo.identity_pair"))
            : source.regions.findIndex(r => r.tooltip);
          source.regions[region].tooltip += "\\n" + "A long documentation line.\\n".repeat(100);
          const container = kind === "slides" ? "#stage" : "#page-" + (number + 1);
          leanTooltips.mount(document.querySelector(container), source);
          return container + " .hover:nth-of-type(" + (region + 1) + ")";
        }""", {"index": index, "kind": kind})
        # SVG is not a button, so nth-of-type selects the metadata overlay index.
        trigger = page.locator(selector)
        trigger.hover()
        tooltip = page.locator("#tooltip")
        expect(tooltip).to_be_visible()
        source_box, popup_box = trigger.bounding_box(), tooltip.bounding_box()
        assert (popup_box["y"] >= source_box["y"] + source_box["height"] + 8 or
                popup_box["y"] + popup_box["height"] <= source_box["y"] - 8)
        changes = tooltip.evaluate("""element => new Promise(resolve => {
          let changes = 0;
          const observer = new MutationObserver(records => { changes += records.length; });
          observer.observe(element, {attributes: true, attributeFilter: ["hidden"]});
          setTimeout(() => { observer.disconnect(); resolve(changes); }, 350);
        })""")
        assert changes == 0, "Tooltip alternated while the pointer stayed over its source"
        tooltip.hover()
        # Stay longer than the close delay: entering the popup must cancel it.
        page.wait_for_timeout(350)
        expect(tooltip).to_be_visible()
        assert tooltip.evaluate("el => el.scrollHeight > el.clientHeight")
        page.evaluate("""() => {
          window.lastWheelTarget = null;
          addEventListener("wheel", event => {
            window.lastWheelTarget = event.target.id || event.target.tagName;
          }, {capture: true, once: true});
        }""")
        page.mouse.wheel(0, 300)
        try:
            page.wait_for_function("document.getElementById('tooltip').scrollTop > 0", timeout=5000)
        except BrowserTimeout as error:
            details = tooltip.evaluate("""el => ({hidden: el.hidden, hovered: el.matches(":hover"),
              scrollTop: el.scrollTop, scrollHeight: el.scrollHeight, clientHeight: el.clientHeight,
              bounds: el.getBoundingClientRect().toJSON(), wheelTarget: window.lastWheelTarget})""")
            raise AssertionError(f"{kind} popup did not scroll: {details}") from error
        expect(tooltip).to_be_visible()
        page.mouse.move(0, 0)
        expect(tooltip).to_be_hidden()
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(url)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--screenshots", type=Path)
    args = parser.parse_args()
    if args.screenshots:
        args.screenshots.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome", headless=True)
        try:
            for kind in ("slides", "article", "book"):
                page = browser.new_page(viewport={"width": 1280, "height": 900})
                errors, network = [], []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("request", lambda request: network.append(request.url)
                        if request.url.startswith(("http:", "https:")) else None)
                url = (ROOT / "documents" / kind / "build/main.html").as_uri()
                page.goto(url)
                if kind == "slides":
                    expect(page.locator("#counter")).to_have_text("1 / 4")
                    page.locator("#next").click()
                    expect(page.locator("#counter")).to_have_text("2 / 4")
                else:
                    assert page.locator(".page").count() >= 2
                    if kind == "book":
                        contents = page.get_by_role("navigation", name="Table of contents")
                        expect(contents.locator("a")).to_have_count(6)
                        expect(contents.locator("ol ol")).to_have_count(2)
                        link = contents.get_by_role("link", name="1.2 A proof with two branches", exact=True)
                        href = link.get_attribute("href")
                        link.click()
                        assert page.evaluate("location.hash") == href
                        page.wait_for_function(
                            "Math.abs(document.querySelector(location.hash).getBoundingClientRect().top - 24) < 2")
                        # A saved section link must also work on a fresh load.
                        page.reload()
                        page.wait_for_function(
                            "Math.abs(document.querySelector(location.hash).getBoundingClientRect().top - 24) < 2")
                bubble = page.locator('.hover[data-role="state"]').first
                bubble.click()
                tooltip = page.locator("#tooltip")
                expect(tooltip).to_be_visible()
                expect(tooltip).to_contain_text("⊢")
                page.mouse.move(0, 0)
                expect(tooltip).to_be_visible()
                page.keyboard.press("Escape")
                expect(tooltip).to_be_hidden()
                check_hover_and_scroll(page, url, kind)
                if args.screenshots:
                    page.screenshot(path=str(args.screenshots / (kind + ".png")))
                page.set_viewport_size({"width": 390, "height": 844})
                page.wait_for_function("document.documentElement.scrollWidth <= innerWidth")
                assert not errors, errors
                assert not network, network
                print(f"{kind}: navigation, non-overlapping hover, popup scrolling, pin/dismiss, mobile layout, and offline loading passed")
                page.close()
        finally:
            browser.close()


if __name__ == "__main__":
    main()
