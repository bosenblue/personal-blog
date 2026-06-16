# Personal Blog

一个适合个人长期维护的静态博客模板，包含：

- 博客文章
- 个人介绍页
- 作品展示页
- Markdown 写作流
- 分类、标签、搜索
- RSS、站点地图
- 深色模式
- 评论与统计预留配置

## 目录结构

```text
personal-blog/
  build.py
  site.yml
  content/
    pages/
    posts/
    projects/
  static/
  templates/
  dist/
```

## 如何写文章

在 `content/posts/` 新建一个 `.md` 文件，格式如下：

```md
---
title: 文章标题
slug: article-slug
date: 2026-06-16T10:00:00
category: 分类名
tags:
  - 标签 1
  - 标签 2
summary: 一句话摘要
featured: false
---

这里开始写正文。
```

作品展示放在 `content/projects/`，个人页面放在 `content/pages/`。

## 生成网站

```bash
python build.py
```

生成结果会输出到 `dist/`。

## 本地预览

在 `personal-blog/` 目录里启动一个简单静态服务即可，例如：

```bash
python -m http.server 8000 -d dist
```

然后访问 `http://localhost:8000`。

## 建议上线方式

默认建议优先考虑静态托管平台。对个人博客最友好的方向通常是：

- Cloudflare Pages：部署简单，速度好，适合个人站
- GitHub Pages：免费，适合和仓库一起管理
- Netlify：功能完整，也比较适合个人项目

## 后续你可能会改的地方

- `site.yml`：站点标题、描述、邮箱、社交链接、评论和统计配置
- `content/`：文章、页面、作品内容
- `static/css/site.css`：视觉样式
- `templates/`：页面结构
