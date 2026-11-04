"""Optional browser smoke check: install Playwright and Google Chrome first."""
import argparse
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


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
                page.goto((ROOT / "documents" / kind / "build/main.html").as_uri())
                if kind == "slides":
                    expect(page.locator("#counter")).to_have_text("1 / 4")
                    page.locator("#next").click()
                    expect(page.locator("#counter")).to_have_text("2 / 4")
                else:
                    assert page.locator(".page").count() >= 2
                    if kind == "book":
                        assert page.locator("#page-links a").count() == page.locator(".page").count()
                        page.locator("#page-links a").last.click()
                        assert page.evaluate("location.hash") == "#page-4"
                bubble = page.locator('.hover[data-role="state"]').first
                bubble.click()
                tooltip = page.locator("#tooltip")
                expect(tooltip).to_be_visible()
                expect(tooltip).to_contain_text("⊢")
                page.mouse.move(0, 0)
                expect(tooltip).to_be_visible()
                page.keyboard.press("Escape")
                expect(tooltip).to_be_hidden()
                if args.screenshots:
                    page.screenshot(path=str(args.screenshots / (kind + ".png")))
                page.set_viewport_size({"width": 390, "height": 844})
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                assert not errors, errors
                assert not network, network
                print(f"{kind}: navigation, Lean tooltip pin/dismiss, mobile layout, and offline loading passed")
                page.close()
        finally:
            browser.close()


if __name__ == "__main__":
    main()
