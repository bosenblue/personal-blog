from __future__ import annotations

import json
import math
import re
import shutil
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from email.utils import format_datetime
from html import escape
from pathlib import Path
from typing import Any

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape


ROOT = Path(__file__).parent
CONTENT_DIR = ROOT / "content"
DIST_DIR = ROOT / "dist"
STATIC_DIR = ROOT / "static"
TEMPLATE_DIR = ROOT / "templates"
CONFIG_PATH = ROOT / "site.yml"


@dataclass
class ContentItem:
    kind: str
    title: str
    slug: str
    url: str
    output_path: Path
    source_path: Path
    html: str
    body: str
    excerpt: str
    summary: str
    date: datetime | None
    updated: datetime | None
    category: str | None
    tags: list[str]
    cover: str | None
    featured: bool
    draft: bool
    order: int
    reading_time: int
    meta: dict[str, Any]


def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
    config.setdefault("site", {})
    config["site"]["year"] = datetime.now().year
    config["site"]["base_url"] = (config["site"].get("base_url") or "").rstrip("/")
    config.setdefault("hero", {})
    config.setdefault("social", [])
    config.setdefault("newsletter", {"enabled": False})
    config.setdefault("comments", {"enabled": False})
    config.setdefault("analytics", {"enabled": False})
    return config


def slugify(value: str) -> str:
    sanitized = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", value.lower(), flags=re.UNICODE)
    sanitized = re.sub(r"-{2,}", "-", sanitized).strip("-")
    return sanitized or "item"


def parse_datetime(raw: str | None) -> datetime | None:
    if not raw:
        return None
    return datetime.fromisoformat(str(raw))


def reading_time_for(text: str) -> int:
    english_words = re.findall(r"[A-Za-z0-9_]+", text)
    cjk_chars = re.findall(r"[\u4e00-\u9fff]", text)
    total_units = len(english_words) + len(cjk_chars)
    return max(1, math.ceil(total_units / 320))


def plain_text(value: str) -> str:
    no_tags = re.sub(r"<[^>]+>", "", value)
    compact = re.sub(r"\s+", " ", no_tags).strip()
    return compact


def split_front_matter(raw_text: str) -> tuple[dict[str, Any], str]:
    if not raw_text.startswith("---"):
        return {}, raw_text
    _, front_matter, body = raw_text.split("---", 2)
    return yaml.safe_load(front_matter) or {}, body.strip()


def markdown_to_html(source: str) -> tuple[str, str]:
    renderer = markdown.Markdown(
        extensions=[
            "extra",
            "admonition",
            "tables",
            "toc",
            "fenced_code",
            "codehilite",
            "sane_lists",
            "nl2br",
        ],
        extension_configs={
            "toc": {"permalink": "#"},
            "codehilite": {"guess_lang": False, "css_class": "codehilite"},
        },
    )
    html = renderer.convert(source)
    toc = getattr(renderer, "toc", "")
    return html, toc


def build_item(source_path: Path, kind: str) -> ContentItem:
    raw_text = source_path.read_text(encoding="utf-8")
    meta, body = split_front_matter(raw_text)
    html, toc = markdown_to_html(body)
    text = plain_text(html)
    summary = meta.get("summary") or text[:140].strip()
    slug = meta.get("slug") or slugify(source_path.stem)
    category = meta.get("category")
    tags = [str(tag) for tag in meta.get("tags", [])]
    date = parse_datetime(meta.get("date"))
    updated = parse_datetime(meta.get("updated"))
    featured = bool(meta.get("featured", False))
    draft = bool(meta.get("draft", False))
    order = int(meta.get("order", 999))
    cover = meta.get("cover")

    if kind == "post":
        url = f"/posts/{slug}/"
        output_path = DIST_DIR / "posts" / slug / "index.html"
    elif kind == "project":
        url = f"/projects/{slug}/"
        output_path = DIST_DIR / "projects" / slug / "index.html"
    else:
        url = "/" if slug == "index" else f"/{slug}/"
        output_path = DIST_DIR / ("index.html" if slug == "index" else Path(slug) / "index.html")

    return ContentItem(
        kind=kind,
        title=meta.get("title", source_path.stem),
        slug=slug,
        url=url,
        output_path=output_path,
        source_path=source_path,
        html=html,
        body=body,
        excerpt=text[:220].strip(),
        summary=summary,
        date=date,
        updated=updated,
        category=category,
        tags=tags,
        cover=cover,
        featured=featured,
        draft=draft,
        order=order,
        reading_time=reading_time_for(text),
        meta={**meta, "toc": toc},
    )


def collect_items(kind: str, folder: str) -> list[ContentItem]:
    items = [build_item(path, kind) for path in sorted((CONTENT_DIR / folder).glob("*.md"))]
    published = [item for item in items if not item.draft]
    if kind == "post":
        published.sort(key=lambda item: item.date or datetime.min, reverse=True)
    else:
        published.sort(key=lambda item: (item.order, item.title.lower()))
    return published


def url_with_base(config: dict[str, Any], path: str) -> str:
    base_url = config["site"].get("base_url", "")
    if not base_url:
        return path
    if path == "/":
        return f"{base_url}/"
    return f"{base_url}{path}"


def absolute_url(config: dict[str, Any], path: str) -> str:
    base_url = config["site"].get("base_url", "")
    return f"{base_url}{path}" if base_url else path


def prepare_dist() -> None:
    if not DIST_DIR.exists():
        DIST_DIR.mkdir(parents=True)
    static_target = DIST_DIR / "static"
    for attempt in range(3):
        try:
            if static_target.exists():
                shutil.rmtree(static_target)
            shutil.copytree(STATIC_DIR, static_target)
            return
        except PermissionError:
            if attempt == 2:
                raise
            time.sleep(0.2 * (attempt + 1))


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def render_template(
    env: Environment,
    template_name: str,
    output_path: Path,
    **context: Any,
) -> None:
    template = env.get_template(template_name)
    write_text(output_path, template.render(**context))


def render_xml(path: Path, content: str) -> None:
    write_text(path, content)


def build_taxonomy(items: list[ContentItem], attribute: str) -> dict[str, list[ContentItem]]:
    groups: dict[str, list[ContentItem]] = defaultdict(list)
    for item in items:
        if attribute == "category":
            value = item.category
            if value:
                groups[str(value)].append(item)
        else:
            for tag in item.tags:
                groups[str(tag)].append(item)
    return dict(sorted(groups.items(), key=lambda pair: pair[0].lower()))


def search_index(items: list[ContentItem]) -> list[dict[str, Any]]:
    return [
        {
            "title": item.title,
            "url": item.url,
            "summary": item.summary,
            "category": item.category or "",
            "tags": item.tags,
            "content": plain_text(item.html),
            "kind": item.kind,
        }
        for item in items
    ]


def rss_feed(config: dict[str, Any], posts: list[ContentItem]) -> str:
    site = config["site"]
    updated = posts[0].date if posts else datetime.now()
    items_xml = []
    for post in posts[:20]:
        pub_date = format_datetime((post.date or datetime.now()).astimezone())
        items_xml.append(
            f"""
      <item>
        <title>{escape(post.title)}</title>
        <link>{escape(absolute_url(config, post.url))}</link>
        <guid>{escape(absolute_url(config, post.url))}</guid>
        <description>{escape(post.summary)}</description>
        <pubDate>{pub_date}</pubDate>
      </item>
            """.strip()
        )
    return f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
  <channel>
    <title>{escape(site.get("title", ""))}</title>
    <link>{escape(site.get("base_url") or "/")}</link>
    <description>{escape(site.get("description", ""))}</description>
    <lastBuildDate>{format_datetime(updated.astimezone())}</lastBuildDate>
    {' '.join(items_xml)}
  </channel>
</rss>
"""


def sitemap(config: dict[str, Any], urls: list[str]) -> str:
    site_url = config["site"].get("base_url", "")
    entries = []
    for url in urls:
        loc = f"{site_url}{url}" if site_url else url
        entries.append(f"<url><loc>{escape(loc)}</loc></url>")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  {' '.join(entries)}
</urlset>
"""


def main() -> None:
    config = load_config()
    prepare_dist()

    posts = collect_items("post", "posts")
    pages = collect_items("page", "pages")
    projects = collect_items("project", "projects")
    page_map = {page.slug: page for page in pages}

    categories = build_taxonomy(posts, "category")
    tags = build_taxonomy(posts, "tags")

    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.globals["site_url"] = lambda path: url_with_base(config, path)
    env.globals["slugify"] = slugify

    shared_context = {
        "config": config,
        "posts": posts,
        "projects": projects,
        "pages": page_map,
        "categories": categories,
        "tags": tags,
    }

    featured_posts = [item for item in posts if item.featured][:3] or posts[:3]
    featured_projects = [item for item in projects if item.featured][:3] or projects[:3]

    render_template(
        env,
        "home.html",
        DIST_DIR / "index.html",
        current_path="/",
        featured_posts=featured_posts,
        featured_projects=featured_projects,
        latest_posts=posts[:6],
        total_posts=len(posts),
        total_projects=len(projects),
        **shared_context,
    )
    render_template(
        env,
        "posts.html",
        DIST_DIR / "posts" / "index.html",
        current_path="/posts/",
        page_title="文章",
        page_description="所有文章按时间倒序排列，支持分类和标签浏览。",
        **shared_context,
    )
    render_template(
        env,
        "projects.html",
        DIST_DIR / "projects" / "index.html",
        current_path="/projects/",
        page_title="作品",
        page_description="整理项目案例、实验作品与长期维护的内容。",
        **shared_context,
    )
    render_template(
        env,
        "search.html",
        DIST_DIR / "search" / "index.html",
        current_path="/search/",
        **shared_context,
    )
    render_template(
        env,
        "taxonomy.html",
        DIST_DIR / "tags" / "index.html",
        current_path="/tags/",
        heading="标签",
        taxonomy=tags,
        taxonomy_path="tags",
        **shared_context,
    )
    render_template(
        env,
        "taxonomy.html",
        DIST_DIR / "categories" / "index.html",
        current_path="/categories/",
        heading="分类",
        taxonomy=categories,
        taxonomy_path="categories",
        **shared_context,
    )

    for name, items in categories.items():
        render_template(
            env,
            "posts.html",
            DIST_DIR / "categories" / slugify(name) / "index.html",
            current_path=f"/categories/{slugify(name)}/",
            page_title=f"分类：{name}",
            page_description=f"浏览分类“{name}”下的所有文章。",
            posts=items,
            projects=projects,
            pages=page_map,
            categories=categories,
            tags=tags,
            config=config,
        )

    for name, items in tags.items():
        render_template(
            env,
            "posts.html",
            DIST_DIR / "tags" / slugify(name) / "index.html",
            current_path=f"/tags/{slugify(name)}/",
            page_title=f"标签：{name}",
            page_description=f"浏览标签“{name}”下的所有文章。",
            posts=items,
            projects=projects,
            pages=page_map,
            categories=categories,
            tags=tags,
            config=config,
        )

    for post in posts:
        render_template(
            env,
            "post.html",
            post.output_path,
            current_path=post.url,
            item=post,
            related_posts=[candidate for candidate in posts if candidate.slug != post.slug][:3],
            **shared_context,
        )

    for project in projects:
        render_template(
            env,
            "project.html",
            project.output_path,
            current_path=project.url,
            item=project,
            **shared_context,
        )

    for page in pages:
        template_name = "page.html"
        render_template(
            env,
            template_name,
            page.output_path,
            current_path=page.url,
            item=page,
            **shared_context,
        )

    render_template(
        env,
        "404.html",
        DIST_DIR / "404.html",
        current_path="/404.html",
        **shared_context,
    )

    write_text(DIST_DIR / "search.json", json.dumps(search_index(posts + projects + pages), ensure_ascii=False, indent=2))
    render_xml(DIST_DIR / "rss.xml", rss_feed(config, posts))

    all_urls = [
        "/",
        "/posts/",
        "/projects/",
        "/about/",
        "/search/",
        "/tags/",
        "/categories/",
        "/rss.xml",
    ]
    all_urls.extend(item.url for item in posts + projects + pages if item.slug != "index")
    render_xml(DIST_DIR / "sitemap.xml", sitemap(config, all_urls))

    print(f"Built site into {DIST_DIR}")


if __name__ == "__main__":
    main()
