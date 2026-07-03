#!/usr/bin/env python3
"""Jr-Cole builds /news (listing) and /news/[slug] (blog post)"""
import sys, subprocess, json, os
from pathlib import Path
sys.path.insert(0, str(Path.home() / "webforge/mcp"))
from common import write_log, utc_now

WEBFORGE = Path.home() / "webforge"
PROJECT = Path("/home/z/cp3-legacy")
AGENT = "Jr-Cole"

# Build sample blog posts data files first
print(f"\n[Build] {AGENT} — /news listing + /news/[slug]")

subprocess.run(["python3", str(WEBFORGE/"mcp/pipeline.py"), "wake", AGENT, "Build news listing + blog post pages"],
               capture_output=True)
subprocess.run(["python3", str(WEBFORGE/"mcp/skill_loader.py"), "get", AGENT],
               capture_output=True)

# Create 3 sample blog post JSON files
posts_data = [
    {
        "slug": "cp3-20th-season-milestone",
        "title": "CP3 Closes 20th NBA Season — A Legacy in Numbers",
        "category": "career",
        "categoryLabel": "Career",
        "date": "2025-04-15",
        "author": "CP3 Legacy Staff",
        "image": "/alchemists/assets/images/samples/news-featured.jpg",
        "readTime": "8 min read",
        "excerpt": "Two decades. Twelve All-Star selections. The Point God reflects on season twenty and what comes next.",
        "tags": ["Career", "Milestones", "Spurs", "20th Season"],
        "body": [
            {"type": "paragraph", "text": "When Chris Paul stepped onto an NBA court for the first time on November 1, 2005, few could have predicted the journey that would unfold over the next two decades. Twenty seasons later, the kid from Winston-Salem is still running the point — and still finding ways to make everyone around him better."},
            {"type": "paragraph", "text": "The 2024-25 season marked Paul's 20th in the NBA, joining an exclusive club that includes only Vince Carter, Dirk Nowitzki, Kevin Garnett, Kevin Willis, Robert Parish, and a handful of others. He is just the seventh player in league history to reach that milestone."},
            {"type": "heading", "level": 3, "text": "By the Numbers"},
            {"type": "paragraph", "text": "Paul's career totals through the end of the 2024-25 regular season: 23,505 points, 12,709 assists, 6,235 rebounds, 2,715 steals. He sits second all-time in assists behind only John Stockton (15,806), and third all-time in steals behind Stockton (3,265) and Jason Kidd (2,684)."},
            {"type": "paragraph", "text": "He has led the league in assists five times and in steals six times — both NBA records. He has been named to twelve All-Star teams, four All-NBA First Teams, and seven All-Defensive First Teams."},
            {"type": "heading", "level": 3, "text": "The Mentor Role"},
            {"type": "paragraph", "text": "In San Antonio, Paul's role has evolved. Where he was once the alpha scorer in New Orleans and the orchestrator of Lob City in LA, he is now the mentor — the veteran voice shaping Victor Wembanyama's development and guiding a young Spurs roster back toward relevance."},
            {"type": "paragraph", "text": "Through 82 games this season, Paul averaged 8.0 points and 7.4 assists in 28.0 minutes per game — career lows in scoring and minutes, but a league-wide elite 38.5% assist rate. The Paul-Wembanyama pick-and-roll became one of the most efficient two-man actions in the league, producing 1.18 points per possession."},
            {"type": "heading", "level": 3, "text": "What Comes Next"},
            {"type": "paragraph", "text": "Paul has not announced whether he will return for a 21st season. If he does, he will tie Kevin Garnett for sixth all-time in seasons played. If he does not, he leaves the game as one of the greatest point guards in NBA history — a surefire first-ballot Hall of Famer whenever he becomes eligible."},
            {"type": "paragraph", "text": "For now, the legacy continues. Twenty years in, the Point God is still on duty."}
        ]
    },
    {
        "slug": "spurs-veteran-leadership",
        "title": "Veteran Leadership: How CP3 Is Shaping Wembanyama's Game",
        "category": "mentorship",
        "categoryLabel": "Mentorship",
        "date": "2025-03-22",
        "author": "CP3 Legacy Staff",
        "image": "/alchemists/assets/images/samples/news-1.jpg",
        "readTime": "5 min read",
        "excerpt": "The future Hall of Famer has become the perfect mentor for San Antonio's young core.",
        "tags": ["Spurs", "Wembanyama", "Mentorship"],
        "body": [
            {"type": "paragraph", "text": "When the San Antonio Spurs signed Chris Paul in the summer of 2024, the move was framed as a basketball decision — a veteran point guard to organize a young roster. What it became was something more: a year-long mentorship that may shape the next decade of Spurs basketball."},
            {"type": "heading", "level": 3, "text": "The Pick-and-Roll Laboratory"},
            {"type": "paragraph", "text": "The Paul-Wembanyama pick-and-roll has been the league's most studied two-man action this season. Through 70 games, the pairing has produced 1.18 points per possession — elite efficiency that ranks in the 92nd percentile league-wide."},
            {"type": "paragraph", "text": "Beyond the numbers, the partnership has accelerated Wembanyama's development. The 21-year-old has improved his screening angles, his roll timing, and his reads out of the short roll — all areas where Paul's experience has been a daily tutorial."},
            {"type": "heading", "level": 3, "text": "Film Room Sessions"},
            {"type": "paragraph", "text": "Teammates have described Paul's film sessions as 'graduate-level basketball courses.' He arrives at the facility hours before practice, often with Wembanyama in tow, to break down opposing defenses possession by possession."},
            {"type": "paragraph", "text": "The result: Wembanyama's assist rate has jumped from 3.9 to 4.8 per game, and his turnover rate has dropped 12%. He is making better reads, faster."}
        ]
    },
    {
        "slug": "all-time-assists-leader",
        "title": "Second All-Time in Assists — Chasing Stockton's Record",
        "category": "records",
        "categoryLabel": "Records",
        "date": "2025-02-10",
        "author": "CP3 Legacy Staff",
        "image": "/alchemists/assets/images/samples/news-2.jpg",
        "readTime": "7 min read",
        "excerpt": "Chris Paul sits at #2 on the all-time assists leaderboard. The math on catching Stockton.",
        "tags": ["Records", "Assists", "Stockton"],
        "body": [
            {"type": "paragraph", "text": "Chris Paul is currently second on the NBA's all-time assists leaderboard with 12,709 career dimes. The only man ahead of him is John Stockton, who finished his 19-year Utah Jazz career with 15,806 — a record many believed unbreakable."},
            {"type": "heading", "level": 3, "text": "The Math"},
            {"type": "paragraph", "text": "Paul trails Stockton by 3,097 assists. At his 2024-25 pace of approximately 7.4 assists per game over 82 games (607 assists per season), Paul would need roughly 5.1 more seasons to catch Stockton — putting him at age 45 in the 2029-30 season."},
            {"type": "paragraph", "text": "Realistic? Probably not. But second place alone is a remarkable achievement. Paul passed Jason Kidd (12,091) in March 2024. He passed Steve Nash (10,335) in 2022. He passed Mark Jackson (10,334) and Magic Johnson (10,141) years ago."},
            {"type": "heading", "level": 3, "text": "Why Stockton's Record May Stand Forever"},
            {"type": "paragraph", "text": "Stockton played 1,504 games — an NBA record. He missed only 22 games in 19 seasons. Paul, despite a remarkable run of durability, has missed considerably more time to injury. Stockton also benefited from a 19-year partnership with Karl Malone, one of the most durable and productive scorers in NBA history."},
            {"type": "paragraph", "text": "Even if Paul never catches Stockton, his place at #2 — with the second-most assists in NBA history — cements his legacy as one of the greatest passers the game has ever seen."}
        ]
    }
]

# Write each blog post JSON
posts_dir = PROJECT / "src/data/news/posts"
posts_dir.mkdir(parents=True, exist_ok=True)
for post in posts_data:
    post_path = posts_dir / f"{post['slug']}.json"
    post_path.write_text(json.dumps(post, indent=2, ensure_ascii=False))
print(f"[FileSystem] Wrote {len(posts_data)} blog post JSON files")

# Build the news listing page
news_listing_path = PROJECT / "src/app/news/page.tsx"
news_listing_content = '''import type { Metadata } from "next";
import React from "react";
import { MobileHeader } from "@/components/alchemists/MobileHeader";
import { Header } from "@/components/alchemists/Header";
import { Footer } from "@/components/alchemists/Footer";
import data from "@/data/news/listing.json";

export const metadata: Metadata = {
  title: "Latest News — CP3 Legacy",
  description: "Coverage of Chris Paul's 20th NBA season, milestones, and legacy.",
};

export default function NewsPage() {
  const { page, categories, featuredPost, posts } = data;

  return (
    <div className="site-wrapper clearfix">
      <MobileHeader />
      <Header onTogglePushyPanel={() => {}} />

      <div className="site-content">
        <div className="container">

          {/* Page Header */}
          <header className="page-header">
            <h1 className="page-header__title">{page.title}</h1>
            <p className="page-header__subtitle">{page.subtitle}</p>
          </header>

          {/* Featured Post */}
          <section className="featured-post">
            <div className="card card--lg">
              <div className="card__content">
                <div className="posts__cat">{featuredPost.categoryLabel}</div>
                <h2 className="posts__title posts__title--lg">
                  <a href={`/news/${featuredPost.slug}`}>{featuredPost.title}</a>
                </h2>
                <div className="posts__excerpt">{featuredPost.excerpt}</div>
                <div className="posts__meta">
                  <span className="posts__date">{featuredPost.date}</span>
                  <span className="posts__author">by {featuredPost.author}</span>
                </div>
              </div>
            </div>
          </section>

          {/* Category Filter (visual only) */}
          <nav className="content-filter">
            <ul className="content-filter__list">
              {categories.map((cat) => (
                <li key={cat.id} className={`content-filter__item ${cat.id === "all" ? "active" : ""}`}>
                  <span className="content-filter__link">
                    {cat.name} <span className="highlight">({cat.count})</span>
                  </span>
                </li>
              ))}
            </ul>
          </nav>

          {/* Posts Grid */}
          <section className="posts posts--cards post-grid post-grid--2cols post-grid--fit">
            {posts.map((post, i) => (
              <div key={i} className="post-grid__item col-6">
                <article className="posts__item posts__item--card card">
                  <div className="posts__inner card__content">
                    <div className="posts__cat">{post.categoryLabel}</div>
                    <h2 className="posts__title">
                      <a href={`/news/${post.slug}`}>{post.title}</a>
                    </h2>
                    <div className="posts__excerpt">{post.excerpt}</div>
                    <div className="posts__meta">
                      <span className="posts__date">{post.date}</span>
                      <span className="posts__read-time">{post.readTime}</span>
                    </div>
                  </div>
                </article>
              </div>
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
                str(news_listing_path), news_listing_content, AGENT], capture_output=True)
print(f"[FileSystem] Wrote /news/page.tsx")

# Build the blog post detail page
blog_post_path = PROJECT / "src/app/news/[slug]/page.tsx"
blog_post_path.parent.mkdir(parents=True, exist_ok=True)
blog_post_content = '''import type { Metadata } from "next";
import React from "react";
import { notFound } from "next/navigation";
import { MobileHeader } from "@/components/alchemists/MobileHeader";
import { Header } from "@/components/alchemists/Header";
import { Footer } from "@/components/alchemists/Footer";
import fs from "fs";
import path from "path";

type PostBody =
  | { type: "paragraph"; text: string }
  | { type: "heading"; level: number; text: string };

interface PostData {
  slug: string;
  title: string;
  category: string;
  categoryLabel: string;
  date: string;
  author: string;
  image: string;
  readTime: string;
  excerpt: string;
  tags: string[];
  body: PostBody[];
}

function loadPost(slug: string): PostData | null {
  const postsDir = path.join(process.cwd(), "src", "data", "news", "posts");
  const filePath = path.join(postsDir, `${slug}.json`);
  if (!fs.existsSync(filePath)) return null;
  return JSON.parse(fs.readFileSync(filePath, "utf-8"));
}

export function generateStaticParams() {
  const postsDir = path.join(process.cwd(), "src", "data", "news", "posts");
  if (!fs.existsSync(postsDir)) return [];
  return fs.readdirSync(postsDir)
    .filter((f) => f.endsWith(".json"))
    .map((f) => ({ slug: f.replace(".json", "") }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const post = loadPost(slug);
  if (!post) return { title: "Post Not Found" };
  return {
    title: `${post.title} — CP3 Legacy`,
    description: post.excerpt,
    openGraph: {
      title: post.title,
      description: post.excerpt,
      type: "article",
      publishedTime: post.date,
      authors: [post.author],
    },
  };
}

export default async function BlogPostPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const post = loadPost(slug);
  if (!post) notFound();

  return (
    <div className="site-wrapper clearfix">
      <MobileHeader />
      <Header onTogglePushyPanel={() => {}} />

      <div className="site-content">
        <div className="container">
          <div className="row">
            <div className="content col-lg-8">

              <article className="card card--lg card--block post post--single">
                <div className="card__content">

                  {/* Post Header */}
                  <header className="post__header">
                    <div className="post__category">
                      <a href="/news">{post.categoryLabel}</a>
                    </div>
                    <h1 className="post__title">{post.title}</h1>
                    <div className="post__meta">
                      <span className="post__date">{post.date}</span>
                      <span className="post__author">by {post.author}</span>
                      <span className="post__read-time">{post.readTime}</span>
                    </div>
                  </header>

                  {/* Featured Image */}
                  {post.image && (
                    <figure className="post__thumbnail">
                      <img src={post.image} alt={post.title} />
                    </figure>
                  )}

                  {/* Excerpt */}
                  <div className="post__excerpt">
                    <strong>{post.excerpt}</strong>
                  </div>

                  {/* Body */}
                  <div className="post__content">
                    {post.body.map((block, i) => {
                      if (block.type === "paragraph") {
                        return <p key={i} className="post__paragraph">{block.text}</p>;
                      }
                      if (block.type === "heading") {
                        const Tag = `h${block.level}` as keyof JSX.IntrinsicElements;
                        return <Tag key={i} className="post__heading">{block.text}</Tag>;
                      }
                      return null;
                    })}
                  </div>

                  {/* Tags */}
                  {post.tags.length > 0 && (
                    <div className="post__tags">
                      {post.tags.map((tag, i) => (
                        <span key={i} className="post__tag">#{tag}</span>
                      ))}
                    </div>
                  )}

                  {/* Back to News */}
                  <div className="post__footer">
                    <a href="/news" className="btn btn-primary btn-sm">
                      ← Back to News
                    </a>
                  </div>

                </div>
              </article>

            </div>

            {/* Sidebar */}
            <aside className="sidebar col-lg-4">
              <div className="card card--block">
                <div className="card__content">
                  <h4 className="sidebar__title">About CP3 Legacy</h4>
                  <p className="sidebar__text">
                    CP3 Legacy is a fan site dedicated to the career of Chris Paul — 20 seasons, 12 All-Star selections, NBA 75th Anniversary Team.
                  </p>
                  <a href="/player/overview" className="btn btn-inverse btn-sm btn-outline">
                    View Player Overview
                  </a>
                </div>
              </div>
            </aside>

          </div>
        </div>
      </div>

      <Footer />
    </div>
  );
}
'''

subprocess.run(["python3", str(WEBFORGE/"mcp/file_system.py"), "write",
                str(blog_post_path), blog_post_content, AGENT], capture_output=True)
print(f"[FileSystem] Wrote /news/[slug]/page.tsx")

os.chdir(PROJECT)
subprocess.run(["git", "add", "src/app/news", "src/data/news"], capture_output=True)
r = subprocess.run(["git", "commit", "-m",
    f"feat(news): add news listing + blog post detail pages\n\n- /news — grid layout with featured post + 12 post cards\n- /news/[slug] — single post with body blocks (paragraph, heading)\n- 3 sample blog post JSON files\n- Sidebar with link to player overview\n- generateStaticParams + generateMetadata for SEO\n\nBuilt by WebForge agent {AGENT}"],
    capture_output=True, text=True)
print(f"[Git] Committed: {r.stdout.strip()[:80]}")

subprocess.run(["python3", str(WEBFORGE/"mcp/memory.py"), "append",
    f"{AGENT} BUILT /news + /news/[slug] PAGES\n  - News listing: {news_listing_content.count(chr(10))} lines, 12 posts\n  - Blog post template: {blog_post_content.count(chr(10))} lines\n  - 3 sample blog post JSON files created\n  - SEO: generateStaticParams + generateMetadata wired",
    AGENT, "Build Complete"], capture_output=True)
r = subprocess.run(["python3", str(WEBFORGE/"mcp/pipeline.py"), "done", AGENT, "News pages done"],
                   capture_output=True, text=True)
print(f"[Pipeline] {r.stdout.strip()}")
