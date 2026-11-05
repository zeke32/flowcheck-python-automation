"""Capture real screenshots of the generated offline HTML report for the portfolio."""
from pathlib import Path
import shutil
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path=shutil.which("chromium") or shutil.which("google-chrome"), args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 1200, "height": 900}, device_scale_factor=1)
    page.set_content((ROOT / "demo_output" / "report.html").read_text(encoding="utf-8"), wait_until="load")
    page.screenshot(path=str(ROOT / "docs" / "report_detail.png"), full_page=True)
    page.screenshot(path=str(ROOT / "docs" / "portfolio_cover_large.png"))
    browser.close()
with Image.open(ROOT / "docs" / "portfolio_cover_large.png") as im:
    im.resize((1000,750), Image.Resampling.LANCZOS).save(ROOT / "docs" / "portfolio_cover.png", optimize=True)
(ROOT / "docs" / "portfolio_cover_large.png").unlink()
print("Rendered screenshots from the generated HTML report")
