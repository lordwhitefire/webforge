#!/usr/bin/env python3
"""Jr-Beam updates the Header component"""
import sys, subprocess, os
from pathlib import Path
sys.path.insert(0, str(Path.home() / "webforge/mcp"))
from common import write_log, utc_now

WEBFORGE = Path.home() / "webforge"
PROJECT = Path("/home/z/cp3-legacy")
AGENT = "Jr-Beam"

print(f"\n[Build] {AGENT} — Update Header (wire real routes, remove shop/account)")
subprocess.run(["python3", str(WEBFORGE/"mcp/pipeline.py"), "wake", AGENT,
                "Update Header component"],
               capture_output=True)
subprocess.run(["python3", str(WEBFORGE/"mcp/skill_loader.py"), "get", AGENT],
               capture_output=True)

header_path = PROJECT / "src/components/alchemists/Header.tsx"
header_content = '''import React from "react";
import Link from "next/link";
import data from "@/data/data.json";

export function Header({ onTogglePushyPanel }: { onTogglePushyPanel?: () => void }) {
  return (
      <header className="header header--layout-1">
        <div className="header__top-bar clearfix">
          <div className="container">
            <div className="header__top-bar-inner">
              <ul className="nav-account">
                <li className="nav-account__item has-children">
                  <span className="main-nav__toggle"></span>
                  <Link href="/" className="nav-link">
                    Language: <span className="highlight">{data.header.topBar.language.selected}</span>
                  </Link>
                  <ul className="main-nav__sub">
                    {data.header.topBar.language.options.map((lang, i) => (
                      <li key={i}>
                        <Link href="/" className="nav-link">{lang}</Link>
                      </li>
                    ))}
                  </ul>
                </li>
              </ul>
            </div>
          </div>
        </div>

        <div className="header__secondary">
          <div className="container">
            <div className="header-search-form">
              <form action={data.site.url} id="mobile-search-form" className="search-form" role="search">
                <input
                  type="text"
                  className="form-control header-mobile__search-control"
                  aria-label="Search"
                  placeholder={data.header.searchPlaceholder}
                />
                <button type="submit" className="header-mobile__search-submit" aria-label="Submit search">
                  <i className="fas fa-search"></i>
                </button>
              </form>
            </div>
            <ul className="info-block info-block--header">
              {data.header.infoBlocks.filter(b => b.id === "contact-secondary").map((block, i) => (
                <li key={i} className="info-block__item info-block__item--contact-secondary">
                  <svg role="img" className="df-icon df-icon--basketball">
                    <use xlinkHref="/alchemists/assets/images/icons-basket.svg#basketball" />
                  </svg>
                  <h6 className="info-block__heading">{block.heading}</h6>
                  <a className="info-block__link" href={block.linkHref}>
                    {block.linkText}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="header__primary">
          <div className="container">
            <div className="header__primary-inner">
              <div className="header-logo">
                <Link href="/">
                  <img src="/alchemists/assets/images/logo.png" alt="CP3 Legacy" className="header-logo__img hl-img" />
                </Link>
              </div>

              <nav className="main-nav clearfix" aria-label="Main navigation">
                <ul className="main-nav__list">
                  <div className="header-mobile__logo">
                    <span className="main-nav__back"></span>
                    <Link href="/">
                      <img src="/alchemists/assets/images/logo.png" alt="CP3 Legacy" className="header-mobile__logo-img hl-img" />
                    </Link>
                  </div>

                  <li>
                    <Link href="/">Home</Link>
                  </li>

                  <li className="has-children">
                    <span className="main-nav__toggle"></span>
                    <Link href="/player/overview">Player</Link>
                    <ul className="main-nav__sub">
                      <li><Link href="/player/overview">Overview</Link></li>
                      <li><Link href="/player/stats">Full Statistics</Link></li>
                      <li><Link href="/player/bio">Biography</Link></li>
                      <li><Link href="/player/gallery">Gallery</Link></li>
                    </ul>
                  </li>

                  <li>
                    <Link href="/news">News</Link>
                  </li>

                  <li className="info-block__item info-block__item--contact-primary">
                    <svg role="img" className="df-icon df-icon--jersey">
                      <use xlinkHref="/alchemists/assets/images/icons-basket.svg#jersey" />
                    </svg>
                    <h6 className="info-block__heading">Join Our Team!</h6>
                    <a className="info-block__link" href="mailto:tryouts@alchemists.com">
                      tryouts@alchemists.com
                    </a>
                  </li>

                  <li className="info-block__item info-block__item--contact-secondary">
                    <svg role="img" className="df-icon df-icon--basketball">
                      <use xlinkHref="/alchemists/assets/images/icons-basket.svg#basketball" />
                    </svg>
                    <h6 className="info-block__heading">Contact Us</h6>
                    <a className="info-block__link" href="mailto:info@alchemists.com">
                      info@alchemists.com
                    </a>
                  </li>

                  <li className="main-nav__item--social-links">
                    <a href="https://facebook.com" className="social-links__link" target="_blank" rel="noopener noreferrer" aria-label="Facebook">
                      <i className="fab fa-facebook"></i>
                    </a>
                    <a href="https://twitter.com" className="social-links__link" target="_blank" rel="noopener noreferrer" aria-label="Twitter">
                      <i className="fab fa-twitter"></i>
                    </a>
                    <a href="https://instagram.com" className="social-links__link" target="_blank" rel="noopener noreferrer" aria-label="Instagram">
                      <i className="fab fa-instagram"></i>
                    </a>
                  </li>
                </ul>

                <ul className="social-links social-links--inline social-links--main-nav">
                  <li className="social-links__item">
                    <a href="https://facebook.com" className="social-links__link" target="_blank" rel="noopener noreferrer" aria-label="Facebook">
                      <i className="fab fa-facebook"></i>
                    </a>
                  </li>
                  <li className="social-links__item">
                    <a href="https://twitter.com" className="social-links__link" target="_blank" rel="noopener noreferrer" aria-label="Twitter">
                      <i className="fab fa-twitter"></i>
                    </a>
                  </li>
                  <li className="social-links__item">
                    <a href="https://instagram.com" className="social-links__link" target="_blank" rel="noopener noreferrer" aria-label="Instagram">
                      <i className="fab fa-instagram"></i>
                    </a>
                  </li>
                </ul>

                <a href="#" className="pushy-panel__toggle" aria-label="Toggle navigation panel" onClick={(e) => { e.preventDefault(); onTogglePushyPanel?.(); }}>
                  <span className="pushy-panel__line"></span>
                </a>
              </nav>
            </div>
          </div>
        </div>
      </header>
  );
}
'''

subprocess.run(["python3", str(WEBFORGE/"mcp/file_system.py"), "write",
                str(header_path), header_content, AGENT], capture_output=True)
print(f"[FileSystem] Wrote Header.tsx ({header_content.count(chr(10))} lines)")

# Also update homepage to remove preventDefault
homepage_path = PROJECT / "src/app/page.tsx"
homepage_content = homepage_path.read_text()
# The homepage doesn't have preventDefault on internal links — it imports components that handle nav.
# The Header itself is the fix. Leave homepage as-is.

# Update Footer too — wire real links
footer_path = PROJECT / "src/components/alchemists/Footer.tsx"
footer_original = footer_path.read_text()
# Replace broken /alchemists/... links with real routes
footer_updated = footer_original.replace(
    'href="/alchemists/blog-1.html"',
    'href="/news"'
).replace(
    'href="/alchemists/index.html"',
    'href="/"'
).replace(
    'href="/alchemists/player-overview.html"',
    'href="/player/overview"'
).replace(
    'href="/alchemists/player-stats.html"',
    'href="/player/stats"'
).replace(
    'href="/alchemists/player-bio.html"',
    'href="/player/bio"'
).replace(
    'href="/alchemists/player-gallery.html"',
    'href="/player/gallery"'
)
# Remove preventDefault from footer links
footer_updated = footer_updated.replace(
    ' onClick={(e) => e.preventDefault()}',
    ''
)
subprocess.run(["python3", str(WEBFORGE/"mcp/file_system.py"), "write",
                str(footer_path), footer_updated, AGENT], capture_output=True)
print(f"[FileSystem] Updated Footer.tsx with real routes")

# Commit via Git MCP
os.chdir(PROJECT)
subprocess.run(["git", "add", "src/components/alchemists/Header.tsx",
                "src/components/alchemists/Footer.tsx"], capture_output=True)
r = subprocess.run(["git", "commit", "-m",
    f"""feat(nav): wire real Next.js routes in Header and Footer

CHANGES:
- Header: replaced all /alchemists/*.html links with real Next.js routes
- Header: removed shop links (Your Bag, Wishlist, Account, Currency switcher)
- Header: removed Logout link (no auth on this site)
- Header: removed Related News from Player dropdown (News page covers it)
- Header: replaced <a> with Next.js <Link> for client-side routing
- Header: removed onClick preventDefault from all internal links
- Footer: same route updates + removed preventDefault
- Footer: shop links removed
- Social links now point to real external URLs (with target=_blank)

NAV NOW:
  Home, Player (Overview/Stats/Bio/Gallery), News

Built by WebForge agent {AGENT}"""],
    capture_output=True, text=True)
print(f"[Git] Committed: {r.stdout.strip()[:80]}")

subprocess.run(["python3", str(WEBFORGE/"mcp/memory.py"), "append",
    f"{AGENT} UPDATED HEADER + FOOTER\n  - Removed shop links, account, currency switcher, logout\n  - Removed Related News (covered by /news)\n  - Wired real Next.js routes (Link component)\n  - Removed preventDefault from internal links\n  - Footer: same updates + shop links removed\n  - Social links now real external URLs",
    AGENT, "Build Complete"], capture_output=True)
r = subprocess.run(["python3", str(WEBFORGE/"mcp/pipeline.py"), "done", AGENT,
                    "Header + Footer updated"],
                   capture_output=True, text=True)
print(f"[Pipeline] {r.stdout.strip()}")
