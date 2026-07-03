#!/usr/bin/env python3
"""Jr-Marble builds /player/bio"""
import sys, subprocess, json
from pathlib import Path
sys.path.insert(0, str(Path.home() / "webforge/mcp"))
from common import write_log, utc_now

WEBFORGE = Path.home() / "webforge"
PROJECT = Path("/home/z/cp3-legacy")
AGENT = "Jr-Marble"

print(f"\n[Build] {AGENT} — /player/bio")
subprocess.run(["python3", str(WEBFORGE/"mcp/pipeline.py"), "wake", AGENT, "Build /player/bio page"],
               capture_output=True)
subprocess.run(["python3", str(WEBFORGE/"mcp/skill_loader.py"), "get", AGENT],
               capture_output=True)

bio_data = json.loads((PROJECT / "src/data/player/bio.json").read_text())
print(f"[FileSystem] Read bio.json — {len(bio_data['bio'])} bio fields")

page_path = PROJECT / "src/app/player/bio/page.tsx"
page_content = '''import type { Metadata } from "next";
import React from "react";
import { MobileHeader } from "@/components/alchemists/MobileHeader";
import { Header } from "@/components/alchemists/Header";
import { Footer } from "@/components/alchemists/Footer";
import data from "@/data/player/bio.json";

export const metadata: Metadata = {
  title: "Player Biography — Chris Paul",
  description: "The life and career of Chris Paul — from Winston-Salem to Wake Forest to NBA greatness.",
};

export default function PlayerBioPage() {
  const { player, bio, earlyLife, college, nbaCareer, internationalCareer, achievements, offCourt, personal } = data;

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
              <div className="player-info__nickname">{player.nickname} — Biography</div>
            </div>
          </div>
        </div>
      </div>

      <div className="site-content">
        <div className="container">

          {/* Quick Bio Card */}
          <section className="player-bio-card">
            <div className="card">
              <div className="card__content">
                <h2 className="player-info__section-title">At a Glance</h2>
                <div className="row">
                  <div className="col-md-6">
                    <p><strong>Full Name:</strong> {bio.fullName}</p>
                    <p><strong>Born:</strong> {bio.born}</p>
                    <p><strong>Birthplace:</strong> {bio.birthplace}</p>
                    <p><strong>Nationality:</strong> {bio.nationality}</p>
                    <p><strong>Height:</strong> {bio.height}</p>
                    <p><strong>Weight:</strong> {bio.weight}</p>
                  </div>
                  <div className="col-md-6">
                    <p><strong>Position:</strong> {bio.position}</p>
                    <p><strong>High School:</strong> {bio.highSchool}</p>
                    <p><strong>College:</strong> {bio.college}</p>
                    <p><strong>NBA Draft:</strong> {bio.nbaDraft}</p>
                    <p><strong>Current Team:</strong> {bio.currentTeam}</p>
                    <p><strong>Agent:</strong> {bio.agent}</p>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* Early Life */}
          <section className="player-bio-section">
            <h2 className="player-info__section-title">{earlyLife.title}</h2>
            {earlyLife.paragraphs.map((p, i) => (
              <p key={i} className="player-bio__paragraph">{p}</p>
            ))}
          </section>

          {/* College */}
          <section className="player-bio-section">
            <h2 className="player-info__section-title">{college.title}</h2>
            {college.paragraphs.map((p, i) => (
              <p key={i} className="player-bio__paragraph">{p}</p>
            ))}
          </section>

          {/* NBA Career */}
          <section className="player-bio-section">
            <h2 className="player-info__section-title">{nbaCareer.title}</h2>
            {nbaCareer.paragraphs.map((p, i) => (
              <p key={i} className="player-bio__paragraph">{p}</p>
            ))}
          </section>

          {/* International Career */}
          <section className="player-bio-section">
            <h2 className="player-info__section-title">{internationalCareer.title}</h2>
            {internationalCareer.paragraphs.map((p, i) => (
              <p key={i} className="player-bio__paragraph">{p}</p>
            ))}
          </section>

          {/* Achievements */}
          <section className="player-bio-achievements">
            <h2 className="player-info__section-title">Achievements & Honors</h2>
            <div className="achievements-list">
              {achievements.map((a, i) => (
                <div key={i} className="achievement-item card">
                  <div className="card__content">
                    <div className="achievement-item__year">{a.year}</div>
                    <h3 className="achievement-item__title">{a.title}</h3>
                    <p className="achievement-item__desc">{a.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Off Court */}
          <section className="player-bio-section">
            <h2 className="player-info__section-title">{offCourt.title}</h2>
            {offCourt.paragraphs.map((p, i) => (
              <p key={i} className="player-bio__paragraph">{p}</p>
            ))}
          </section>

          {/* Personal */}
          <section className="player-bio-section">
            <h2 className="player-info__section-title">{personal.title}</h2>
            {personal.paragraphs.map((p, i) => (
              <p key={i} className="player-bio__paragraph">{p}</p>
            ))}
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

import os
os.chdir(PROJECT)
subprocess.run(["git", "add", "src/app/player/bio/page.tsx"], capture_output=True)
subprocess.run(["git", "commit", "-m",
    f"feat(player): add biography page\n\n- Full life story: childhood, Wake Forest, NBA, off-court\n- 11 achievements listed with years\n- International career (Team USA, 2× Olympic Gold)\n- Personal life and foundation work\n\nBuilt by WebForge agent {AGENT}"],
    capture_output=True)
print(f"[Git] Committed bio page")

subprocess.run(["python3", str(WEBFORGE/"mcp/memory.py"), "append",
    f"{AGENT} BUILT /player/bio PAGE — {page_content.count(chr(10))} lines. Includes early life, college, NBA, international, achievements, off-court, personal.",
    AGENT, "Build Complete"], capture_output=True)
r = subprocess.run(["python3", str(WEBFORGE/"mcp/pipeline.py"), "done", AGENT, "Bio page done"],
                   capture_output=True, text=True)
print(f"[Pipeline] {r.stdout.strip()}")
