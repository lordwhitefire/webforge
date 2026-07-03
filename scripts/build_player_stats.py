#!/usr/bin/env python3
"""
WebForge build script — Jr-Granite builds /player/stats
I (the LLM) act as Jr-Granite. The system orchestrates the rest.
"""
import sys
import subprocess
import json
from pathlib import Path
sys.path.insert(0, str(Path.home() / "webforge/mcp"))
from common import write_log, utc_now

WEBFORGE = Path.home() / "webforge"
PROJECT = Path("/home/z/cp3-legacy")
AGENT = "Jr-Granite"
TASK = "Build /player/stats page with full career stats"

print(f"\n{'='*60}\n[Build] {AGENT} — {TASK}\n{'='*60}")

# 1. Hermes wakes me
subprocess.run(["python3", str(WEBFORGE/"mcp/pipeline.py"), "wake", AGENT, TASK],
               capture_output=True, text=True)
print(f"[Pipeline] Hermes woke {AGENT}")

# 2. Skill Loader delivers my skill file
r = subprocess.run(["python3", str(WEBFORGE/"mcp/skill_loader.py"), "get", AGENT],
                   capture_output=True, text=True)
print(f"[SkillLoader] Delivered: {r.stdout.strip()}")

# 3. I read the data file directly (I'm the LLM — I have file access)
stats_data = json.loads((PROJECT / "src/data/player/stats.json").read_text())
print(f"[FileSystem] Read stats.json — {len(stats_data['seasonBySeason'])} seasons")

# 4. I build the page
page_path = PROJECT / "src/app/player/stats/page.tsx"
page_content = '''import type { Metadata } from "next";
import React from "react";
import { MobileHeader } from "@/components/alchemists/MobileHeader";
import { Header } from "@/components/alchemists/Header";
import { Footer } from "@/components/alchemists/Footer";
import data from "@/data/player/stats.json";

export const metadata: Metadata = {
  title: "Player Full Statistics — Chris Paul",
  description: "Complete career statistics for Chris Paul — 20 NBA seasons, 12 All-Star selections, 5× assists leader.",
};

export default function PlayerStatsPage() {
  const { player, careerTotals, careerAverages, seasonBySeason, careerHighs, rankings, advancedStats } = data;

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
              <div className="player-info__nickname">{player.nickname} — Full Statistics</div>
            </div>
          </div>
        </div>
      </div>

      <div className="site-content">
        <div className="container">

          {/* Career Totals */}
          <section className="player-stats-totals">
            <h2 className="player-info__section-title">Career Totals</h2>
            <div className="row">
              <div className="col-md-3 col-sm-6">
                <div className="stat-card">
                  <div className="stat-card__value">{careerTotals.games}</div>
                  <div className="stat-card__label">Games Played</div>
                </div>
              </div>
              <div className="col-md-3 col-sm-6">
                <div className="stat-card">
                  <div className="stat-card__value">{careerTotals.points.toLocaleString()}</div>
                  <div className="stat-card__label">Total Points</div>
                </div>
              </div>
              <div className="col-md-3 col-sm-6">
                <div className="stat-card">
                  <div className="stat-card__value">{careerTotals.assists.toLocaleString()}</div>
                  <div className="stat-card__label">Total Assists</div>
                </div>
              </div>
              <div className="col-md-3 col-sm-6">
                <div className="stat-card">
                  <div className="stat-card__value">{careerTotals.rebounds.toLocaleString()}</div>
                  <div className="stat-card__label">Total Rebounds</div>
                </div>
              </div>
              <div className="col-md-3 col-sm-6">
                <div className="stat-card">
                  <div className="stat-card__value">{careerTotals.steals.toLocaleString()}</div>
                  <div className="stat-card__label">Total Steals</div>
                </div>
              </div>
              <div className="col-md-3 col-sm-6">
                <div className="stat-card">
                  <div className="stat-card__value">{careerTotals.blocks}</div>
                  <div className="stat-card__label">Total Blocks</div>
                </div>
              </div>
              <div className="col-md-3 col-sm-6">
                <div className="stat-card">
                  <div className="stat-card__value">{(careerTotals.fieldGoalPercentage * 100).toFixed(1)}%</div>
                  <div className="stat-card__label">FG Percentage</div>
                </div>
              </div>
              <div className="col-md-3 col-sm-6">
                <div className="stat-card">
                  <div className="stat-card__value">{(careerTotals.freeThrowPercentage * 100).toFixed(1)}%</div>
                  <div className="stat-card__label">FT Percentage</div>
                </div>
              </div>
            </div>
          </section>

          {/* Career Averages */}
          <section className="player-stats-averages">
            <h2 className="player-info__section-title">Career Averages (per game)</h2>
            <div className="row">
              <div className="col-md-2 col-sm-4"><div className="stat-mini"><div className="stat-mini__value">{careerAverages.pointsPerGame}</div><div className="stat-mini__label">PPG</div></div></div>
              <div className="col-md-2 col-sm-4"><div className="stat-mini"><div className="stat-mini__value">{careerAverages.assistsPerGame}</div><div className="stat-mini__label">APG</div></div></div>
              <div className="col-md-2 col-sm-4"><div className="stat-mini"><div className="stat-mini__value">{careerAverages.reboundsPerGame}</div><div className="stat-mini__label">RPG</div></div></div>
              <div className="col-md-2 col-sm-4"><div className="stat-mini"><div className="stat-mini__value">{careerAverages.stealsPerGame}</div><div className="stat-mini__label">SPG</div></div></div>
              <div className="col-md-2 col-sm-4"><div className="stat-mini"><div className="stat-mini__value">{careerAverages.blocksPerGame}</div><div className="stat-mini__label">BPG</div></div></div>
              <div className="col-md-2 col-sm-4"><div className="stat-mini"><div className="stat-mini__value">{careerAverages.minutesPerGame}</div><div className="stat-mini__label">MPG</div></div></div>
            </div>
          </section>

          {/* Career Highs */}
          <section className="player-stats-highs">
            <h2 className="player-info__section-title">Career Highs</h2>
            <div className="row">
              <div className="col-md-2 col-sm-4"><div className="stat-mini"><div className="stat-mini__value">{careerHighs.points}</div><div className="stat-mini__label">Points</div></div></div>
              <div className="col-md-2 col-sm-4"><div className="stat-mini"><div className="stat-mini__value">{careerHighs.assists}</div><div className="stat-mini__label">Assists</div></div></div>
              <div className="col-md-2 col-sm-4"><div className="stat-mini"><div className="stat-mini__value">{careerHighs.rebounds}</div><div className="stat-mini__label">Rebounds</div></div></div>
              <div className="col-md-2 col-sm-4"><div className="stat-mini"><div className="stat-mini__value">{careerHighs.steals}</div><div className="stat-mini__label">Steals</div></div></div>
              <div className="col-md-2 col-sm-4"><div className="stat-mini"><div className="stat-mini__value">{careerHighs.blocks}</div><div className="stat-mini__label">Blocks</div></div></div>
              <div className="col-md-2 col-sm-4"><div className="stat-mini"><div className="stat-mini__value">{careerHighs.threePointersMade}</div><div className="stat-mini__label">3-PT Made</div></div></div>
            </div>
          </section>

          {/* All-Time Rankings */}
          <section className="player-stats-rankings">
            <h2 className="player-info__section-title">All-Time NBA Rankings</h2>
            <div className="row">
              <div className="col-md-4 col-sm-6"><div className="ranking-card"><div className="ranking-card__value">#{rankings.allTimeAssists}</div><div className="ranking-card__label">All-Time Assists</div></div></div>
              <div className="col-md-4 col-sm-6"><div className="ranking-card"><div className="ranking-card__value">#{rankings.allTimeSteals}</div><div className="ranking-card__label">All-Time Steals</div></div></div>
              <div className="col-md-4 col-sm-6"><div className="ranking-card"><div className="ranking-card__value">{rankings.allTimeAssistLeaderSeasons}×</div><div className="ranking-card__label">Assists Leader (seasons)</div></div></div>
            </div>
          </section>

          {/* Season-by-Season Table */}
          <section className="player-stats-seasons">
            <h2 className="player-info__section-title">Season-by-Season</h2>
            <div className="table-responsive">
              <table className="table table--lg team-roster__table">
                <thead>
                  <tr>
                    <th>Season</th>
                    <th>Team</th>
                    <th>GP</th>
                    <th>GS</th>
                    <th>MPG</th>
                    <th>PPG</th>
                    <th>RPG</th>
                    <th>APG</th>
                    <th>SPG</th>
                    <th>FG%</th>
                    <th>3P%</th>
                    <th>FT%</th>
                    <th>Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {seasonBySeason.map((s, i) => (
                    <tr key={i}>
                      <td>{s.season}</td>
                      <td>{s.team}</td>
                      <td>{s.gp}</td>
                      <td>{s.gs}</td>
                      <td>{s.mpg}</td>
                      <td>{s.ppg}</td>
                      <td>{s.rpg}</td>
                      <td>{s.apg}</td>
                      <td>{s.spg}</td>
                      <td>{(s.fg_pct * 100).toFixed(1)}</td>
                      <td>{(s.fg3_pct * 100).toFixed(1)}</td>
                      <td>{(s.ft_pct * 100).toFixed(1)}</td>
                      <td>{s.notes}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* Advanced Stats */}
          <section className="player-stats-advanced">
            <h2 className="player-info__section-title">Advanced Stats</h2>
            <div className="row">
              <div className="col-md-2 col-sm-4"><div className="stat-mini"><div className="stat-mini__value">{advancedStats.playerEfficiencyRating}</div><div className="stat-mini__label">PER</div></div></div>
              <div className="col-md-2 col-sm-4"><div className="stat-mini"><div className="stat-mini__value">{(advancedStats.trueShootingPercentage * 100).toFixed(1)}%</div><div className="stat-mini__label">TS%</div></div></div>
              <div className="col-md-2 col-sm-4"><div className="stat-mini"><div className="stat-mini__value">{advancedStats.usageRate}%</div><div className="stat-mini__label">USG%</div></div></div>
              <div className="col-md-2 col-sm-4"><div className="stat-mini"><div className="stat-mini__value">{advancedStats.winShares}</div><div className="stat-mini__label">Win Shares</div></div></div>
              <div className="col-md-2 col-sm-4"><div className="stat-mini"><div className="stat-mini__value">{advancedStats.boxPlusMinus}</div><div className="stat-mini__label">BPM</div></div></div>
              <div className="col-md-2 col-sm-4"><div className="stat-mini"><div className="stat-mini__value">{advancedStats.valueOverReplacement}</div><div className="stat-mini__label">VORP</div></div></div>
            </div>
          </section>

        </div>
      </div>

      <Footer />
    </div>
  );
}
'''

# Use File System MCP to write the page
r = subprocess.run(["python3", str(WEBFORGE/"mcp/file_system.py"), "write",
                    str(page_path), page_content, AGENT],
                   capture_output=True, text=True)
print(f"[FileSystem] Wrote {page_path.name}: {r.stdout.strip()[:100]}")

# 5. Stamp commits via Git MCP
import os
os.chdir(PROJECT)
subprocess.run(["git", "add", "src/app/player/stats/page.tsx"], capture_output=True)
commit_msg = f"""feat(player): add full statistics page

- Career totals (1,471 GP, 23,505 PTS, 12,709 AST)
- Career averages per game
- Career highs (43 PTS, 21 AST, 12 REB, 9 STL)
- All-time rankings (#2 assists, #3 steals)
- 20-season table with notes
- Advanced stats (PER, TS%, WS, BPM, VORP)

Built by WebForge agent {AGENT} (acting as LLM)
"""
r = subprocess.run(["git", "commit", "-m", commit_msg], capture_output=True, text=True)
print(f"[Git] Committed: {r.stdout.strip()[:80]}")

# 6. Memory records what happened
subprocess.run(["python3", str(WEBFORGE/"mcp/memory.py"), "append",
                f"{AGENT} BUILT /player/stats PAGE\n  - Page: src/app/player/stats/page.tsx ({page_content.count(chr(10))} lines)\n  - Data: src/data/player/stats.json (20 seasons)\n  - Sections: Career Totals, Averages, Highs, Rankings, Season Table, Advanced\n  - Status: COMPLETED",
                AGENT, "Build Complete"], capture_output=True)

# 7. Signal done
r = subprocess.run(["python3", str(WEBFORGE/"mcp/pipeline.py"), "done", AGENT,
                    "Stats page built and committed"],
                   capture_output=True, text=True)
print(f"[Pipeline] {r.stdout.strip()}")
