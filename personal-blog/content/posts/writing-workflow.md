---
title: 我准备怎样维护这个博客
slug: writing-workflow
date: 2026-06-15T19:30:00
category: 写作方法
tags:
  - 工作流
  - 内容管理
  - 效率
featured: true
summary: 先把写作流程做得简单，才更容易长期坚持。这里记录我准备采用的博客维护方式。
---

我希望这个博客的维护方式尽可能简单，所以流程会保持轻量：

1. 新建一篇 Markdown 文件
2. 填写标题、日期、分类、标签
3. 写正文
4. 生成静态页面并发布

## 一篇文章最少需要哪些信息

- `title`：文章标题
- `date`：发布日期
- `category`：所属分类
- `tags`：标签
- `summary`：摘要

## 这套方式的好处

它不依赖复杂后台，也不用担心服务迁移时内容被锁住。文件都在自己手里，长期看更安心。

```python
def publish(post):
    return f"发布：{post['title']}"
```
