#!/usr/bin/env python3
"""Blackthorn Rootworks single-page structural validation (not WCAG certification)."""
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree

ROOT=Path(__file__).resolve().parents[1]
class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids=[]
        self.refs=[]
        self.images=[]
        self.lang=None
        self.h1=0
        self.mains=[]
        self.skip_links=[]
        self.header_seen=False
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=="html": self.lang=a.get("lang")
        if tag=="header": self.header_seen=True
        if tag=="main": self.mains.append(a)
        if tag=="h1": self.h1+=1
        if a.get("id"): self.ids.append(a["id"])
        if tag=="img": self.images.append(a)
        if tag=="a" and "skip-link" in (a.get("class") or "").split():
            self.skip_links.append((a.get("href"),self.header_seen))
        for key in ("href","src"):
            if a.get(key): self.refs.append(a[key])

def main():
    page=Page()
    page.feed((ROOT/"index.html").read_text(encoding="utf-8"))
    issues=[]
    if page.lang!="en": issues.append("Document lacks lang=en")
    if len(page.mains)!=1 or page.mains[0].get("id")!="top" or page.mains[0].get("tabindex")!="-1":
        issues.append("Expected one focusable main#top")
    if page.skip_links!=[("#top",False)]: issues.append("Expected skip link before header")
    if page.h1!=1: issues.append(f"Expected one h1, got {page.h1}")
    for name,n in Counter(page.ids).items():
        if n>1: issues.append(f"Duplicate HTML id: {name}")
    for img in page.images:
        if "alt" not in img: issues.append(f"Image missing alt attribute: {img.get('src')}")
    for url in page.refs:
        p=urlsplit(url)
        if p.scheme or p.netloc or url.startswith("//"): continue
        target=(ROOT/unquote(p.path.lstrip("/"))).resolve() if p.path else ROOT/"index.html"
        if not target.is_relative_to(ROOT.resolve()) or not target.is_file():
            issues.append(f"Broken local file reference: {url}")
        if p.fragment and p.fragment not in page.ids:
            issues.append(f"Broken internal anchor: {url}")
    style=(ROOT/"assets/css/styles.css").read_text(encoding="utf-8")
    if not all(v in style for v in (".skip-link:focus",":focus-visible","prefers-reduced-motion")):
        issues.append("Expected skip-link focus, visible focus and reduced-motion styles")
    if (ROOT/"CNAME").read_text(encoding="utf-8").strip()!="rootworks.technerd.tech":
        issues.append("Custom-domain CNAME mismatch")
    document=(ROOT/"index.html").read_text(encoding="utf-8")
    canonical='https://rootworks.technerd.tech/'
    if f'<link rel="canonical" href="{canonical}">' not in document:
        issues.append("Canonical homepage link missing or inconsistent")
    robots=(ROOT/"robots.txt").read_text(encoding="utf-8")
    if "Sitemap: https://rootworks.technerd.tech/sitemap.xml" not in robots:
        issues.append("robots.txt is missing the sitemap link")
    try:
        root=ElementTree.parse(ROOT/"sitemap.xml").getroot()
        locs=[e.text for e in root.findall("{http://www.sitemaps.org/schemas/sitemap/0.9}url/{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
        if locs != [canonical]:
            issues.append(f"Unexpected sitemap URLs: {locs}")
    except (OSError, ElementTree.ParseError) as error:
        issues.append(f"Invalid sitemap.xml: {error}")
    if issues:
        print("Rootworks structural validation FAILED:")
        for error in issues: print(" -",error)
        raise SystemExit(1)
    print(f"Rootworks structural validation PASSED: {len(page.refs)} references, {len(page.images)} images, headings, focus, reduced-motion, CNAME")

if __name__=="__main__": main()
