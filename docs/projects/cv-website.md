---
title: "Personal Portfolio Website"  
description: "A highly customized static site built with Material for MkDocs, featuring dynamic BibTeX parsing, rotating bento grids, and a neon-glassmorphism aesthetic."  
tags:
  - Python
  - CI/CD
  - CSS
  - Jinja2
  - HTML
date: 2026-01-27  
weight: 100
---

# {{ title }}

<div class="hero-section" style="padding: 2rem 0; text-align: left;">  
<p class="hero-subtitle" style="margin: 0; max-width: 100%;">  
You are looking at it right now! This website is a "meta-project" designed to be more than just a resume—it is a playground for static site generation experiments and automation.  
</p>  
<div style="margin-top: 20px;">  
<a href="https://www.google.com/search?q=https://github.com/YOUR\_USERNAME/YOUR\_REPO" class="neon-button">View Source Code</a>  
</div>  
</div>

## 🚀 The Motivation

Standard academic websites are often functional but dry. I wanted a platform that could:

1. **Automate maintenance:** Update my CV automatically when I push a new BibTeX entry.  
2. **Showcase personality:** Move away from standard bootstrap themes to a modern *Glassmorphism* aesthetic.  
3. **Experiment with UX:** Implement interactive elements like the "Rotating Bento Grid" to surface buried content.

## 🛠️ Key Technical Features

This isn't just a standard theme configuration. It relies on a custom Python build pipeline (main.py) that hooks into the MkDocs build process.  
<div class="bento-grid" style="grid-template-columns: 1fr; grid-auto-rows: auto;"> 
<div class="bento-card">  
<div class="card-static-header">  
<i class="fa-solid fa-book card-header-icon"></i>  
<span class="card-header-title">Dynamic Bibliography</span>  
</div>  
<p class="subtext">  
A custom Python script parses my <code>publications.bib</code> file during the build. It generates:
    <ul>
      <li>A sortable, filterable main list.</li>
      <li>Individual Markdown pages for every single paper with abstract and citation buttons.  </li>
    </ul>
</p>  
</div>  
<div class="bento-card">  
    <div class="card-static-header">  
        <i class="fa-solid fa-rotate card-header-icon"></i>  
        <span class="card-header-title">Jinja2 Macros</span>  
    </div>  
    <p class="subtext">  
        I wrote custom macros like <code>generate_rotating_grid()</code> that scan my content folders, extract metadata (YAML frontmatter), and render interactive, rotating cards that pause on hover and support deep linking.  
    </p>  
</div>

<div class="bento-card">  
    <div class="card-static-header">  
        <i class="fa-solid fa-palette card-header-icon"></i>  
        <span class="card-header-title">Custom CSS Theme</span>  
    </div>  
    <p class="subtext">  
        A complete override of the Material for MkDocs colors using CSS variables to create a dark-mode "Neon Glass" aesthetic with backdrop filters, gradients, and animated progress bars.  
    </p>  
</div>

</div>

## 💻 Tech Stack

<div style="display: flex; gap: 10px; flex-wrap: wrap; margin-top: 1rem; margin-bottom: 2rem;">  
<span class="tech-tag">Python</span>  
<span class="tech-tag">Material for MkDocs</span>  
<span class="tech-tag">Jinja2</span>  
<span class="tech-tag">CSS3</span>  
<span class="tech-tag">GitHub Actions</span>  
</div>

## 🔄 Automated Deployment

The site is built using a **CI/CD pipeline** on GitHub Actions. It follows a modern "Infrastructure as Code" approach:

1. Trigger: Push to main branch.  
2. Build: A uv-optimized Python environment installs dependencies.  
3. Generate: main.py runs, converting BibTeX and Markdown data into HTML structures.  
4. Deploy: mkdocs build compiles the final site, which is pushed natively to GitHub Pages via artifacts.