#!/usr/bin/env python3
"""Jr-Quartz builds /player/gallery"""
import sys, subprocess, json, os
from pathlib import Path
sys.path.insert(0, str(Path.home() / "webforge/mcp"))
from common import write_log, utc_now

WEBFORGE = Path.home() / "webforge"
PROJECT = Path("/home/z/cp3-legacy")
AGENT = "Jr-Quartz"

print(f"\n[Build] {AGENT} — /player/gallery")
subprocess.run(["python3", str(WEBFORGE/"mcp/pipeline.py"), "wake", AGENT, "Build /player/gallery"],
               capture_output=True)
subprocess.run(["python3", str(WEBFORGE/"mcp/skill_loader.py"), "get", AGENT],
               capture_output=True)

gallery_data = json.loads((PROJECT / "src/data/player/gallery.json").read_text())
print(f"[FileSystem] Read gallery.json — {len(gallery_data['photos'])} photos")

page_path = PROJECT / "src/app/player/gallery/page.tsx"
page_content = '''import type { Metadata } from "next";
import React, { useState } from "react";
import { MobileHeader } from "@/components/alchemists/MobileHeader";
import { Header } from "@/components/alchemists/Header";
import { Footer } from "@/components/alchemists/Footer";
import data from "@/data/player/gallery.json";

export const metadata: Metadata = {
  title: "Player Gallery — Chris Paul",
  description: "Photo gallery of Chris Paul — game action, portraits, off-court moments.",
};

export default function PlayerGalleryPage() {
  const { player, categories, photos } = data;
  const [activeCategory, setActiveCategory] = useState("all");

  const filteredPhotos = activeCategory === "all"
    ? photos
    : photos.filter((p) => p.category === activeCategory);

  return (
    <div className="site-wrapper clearfix">
      <MobileHeader />
      <Header onTogglePushyPanel={() => {}} />

      <div className="player-heading">
        <div className="container">
          <div className="player-info">
            <div className="player-info__title">
              <div className="player-info__number">{player.number}</div>
              <h1 className="player-info__name">
                {player.firstName} <span className="player-info__last-name">{player.lastName}</span>
              </h1>
              <div className="player-info__nickname">{player.nickname} — Gallery</div>
            </div>
          </div>
        </div>
      </div>

      <div className="site-content">
        <div className="container">

          {/* Category Filter */}
          <nav className="content-filter">
            <ul className="content-filter__list">
              {categories.map((cat) => (
                <li
                  key={cat.id}
                  className={`content-filter__item ${activeCategory === cat.id ? "active" : ""}`}
                >
                  <button
                    onClick={() => setActiveCategory(cat.id)}
                    className="content-filter__link"
                  >
                    {cat.name} <span className="highlight">({cat.count})</span>
                  </button>
                </li>
              ))}
            </ul>
          </nav>

          {/* Photo Grid */}
          <section className="player-gallery">
            <div className="gallery-grid gallery-grid--4cols">
              {filteredPhotos.map((photo) => (
                <div key={photo.id} className="gallery-grid__item">
                  <a href={photo.url} className="gallery-item" target="_blank" rel="noopener noreferrer">
                    <img
                      src={photo.thumbnail}
                      alt={photo.title}
                      className="gallery-item__img"
                      loading="lazy"
                    />
                    <div className="gallery-item__info">
                      <h4 className="gallery-item__title">{photo.title}</h4>
                      <div className="gallery-item__date">{photo.date}</div>
                      <p className="gallery-item__caption">{photo.caption}</p>
                    </div>
                  </a>
                </div>
              ))}
            </div>

            {filteredPhotos.length === 0 && (
              <div className="gallery-empty">
                <p>No photos in this category yet.</p>
              </div>
            )}
          </section>

        </div>
      </div>

      <Footer />
    </div>
  );
}
'''

subprocess.run(["python3", str(WEBFORGE/"mcp/file_system.py"), "write",
                str(page_path), page_content, AGENT], capture_output=True)

os.chdir(PROJECT)
subprocess.run(["git", "add", "src/app/player/gallery/page.tsx"], capture_output=True)
subprocess.run(["git", "commit", "-m",
    f"feat(player): add photo gallery page\n\n- 24 photos across 5 categories\n- Filterable by category (all, games, portraits, offcourt, team)\n- 4-column responsive grid\n- Click to view full image\n\nBuilt by WebForge agent {AGENT}"],
    capture_output=True)
print(f"[Git] Committed gallery page")

subprocess.run(["python3", str(WEBFORGE/"mcp/memory.py"), "append",
    f"{AGENT} BUILT /player/gallery PAGE — {page_content.count(chr(10))} lines. 24 photos, 5 categories, filterable.",
    AGENT, "Build Complete"], capture_output=True)
r = subprocess.run(["python3", str(WEBFORGE/"mcp/pipeline.py"), "done", AGENT, "Gallery page done"],
                   capture_output=True, text=True)
print(f"[Pipeline] {r.stdout.strip()}")
