import bibtexparser
import os
import re
from textwrap import dedent
from markupsafe import Markup
import frontmatter
import datetime
import markdown
import random

# --- CONFIGURATION ---
BIB_FILE = "docs/assets/publications.bib"
PUB_OUTPUT_DIR = "docs/publications"
# Path where the script looks for images to include on the page
# Example: docs/assets/images/publications/my_paper_key.png
PUB_IMAGE_DIR_REL = "assets/images/publications" 
PUB_IMAGE_DIR_ABS = "docs/assets/images/publications"

def load_bib_data(bib_file):
    if not os.path.exists(bib_file):
        return []
    with open(bib_file, encoding='utf-8') as bibtex_file:
        bib_database = bibtexparser.load(bibtex_file)
    return sorted(bib_database.entries, key=lambda x: x.get('year', '0'), reverse=True)

def clean_text(text):
    """Cleans BibTeX braces and newlines."""
    if not text: return ""
    return text.replace("{", "").replace("}", "").replace('\n', ' ').strip()

def format_authors(entry):
    raw_authors = entry.get('author', 'Unknown').replace('\n', ' ')
    formatted_authors = []
    for name in raw_authors.split(' and '):
        parts = name.split(',', 1)
        if len(parts) == 2:
            formatted_authors.append(f"{parts[1].strip()} {parts[0].strip()}")
        else:
            formatted_authors.append(name.strip())
    return ", ".join(formatted_authors)

def _slugify(text):
    """
    Simple slugify function to match MkDocs behavior.
    Converts 'Title - Subtitle' to 'title---subtitle'.
    """
    text = text.lower()
    # Remove characters that aren't alphanumerics, underscores, hyphens, or spaces
    text = re.sub(r'[^\w\s-]', '', text)
    # Replace spaces with hyphens
    text = text.strip().replace(' ', '-')
    return text

def generate_buttons_html(entry):
    """
    Generates the HTML for the PDF, DOI, ArXiv, and Code buttons.
    """
    citation_key = entry.get('ID')
    buttons = []
    
    # --- A. PDF Button ---
    pdf_link = entry.get('pdf') or entry.get('file')
    if not pdf_link:
        local_path = f"docs/pdfs/publications/{citation_key}.pdf"
        if os.path.exists(local_path):
            pdf_link = f"/pdfs/publications/{citation_key}.pdf"
    
    if pdf_link:
        buttons.append(f'<a href="{pdf_link}" class="table-icon" target="_blank" title="PDF"><i class="fa-solid fa-file-pdf"></i> </a>')

    # --- B. DOI Button ---
    doi = entry.get('doi')
    if doi:
        if not doi.startswith('http'):
            doi = f"https://doi.org/{doi}"
        buttons.append(f'<a href="{doi}" class="table-icon" target="_blank" title="DOI"><i class="ai ai-doi"></i> </a>')

    # --- C. ArXiv Button ---
    arxiv_val = entry.get('arxiv') or entry.get('eprint')
    main_url = entry.get('url') or entry.get('link') or ""
    
    arxiv_link = None
    if arxiv_val:
        arxiv_link = arxiv_val if arxiv_val.startswith('http') else f"https://arxiv.org/abs/{arxiv_val}"
    elif "arxiv.org" in main_url:
        arxiv_link = main_url
    
    if arxiv_link:
        buttons.append(f'<a href="{arxiv_link}" class="table-icon" target="_blank" title="ArXiv"><i class="ai ai-arxiv"></i> </a>')

    # --- D. Code Button ---
    code_link = entry.get('code') or entry.get('github') or entry.get('repository')
    if code_link:
        buttons.append(f'<a href="{code_link}" class="table-icon" target="_blank" title="Code"><i class="fa-brands fa-github"></i> </a>')
            
    return "\n".join(buttons)

def create_publication_pages():
    """
    Generates a Markdown file for each publication in the BibTeX file.
    Includes 'description' and 'date' in frontmatter.
    """
    entries = load_bib_data(BIB_FILE)
    if not entries:
        return

    # Ensure output directory exists
    os.makedirs(PUB_OUTPUT_DIR, exist_ok=True)

    # Template with description and date fields in frontmatter
    md_template = """---
title: "{title}"
description: "{description}"
date: "{date}"
hide:
  - nav
---

<div class="pub-page-layout">
    
    <div class="pub-header">
        <h1>{title}</h1>
        <div class="pub-meta">
            <span class="pub-venue">{venue}</span>
            <span class="pub-year">{year}</span>
        </div>
        <div class="pub-authors-list">{authors}</div>
        <div class="pub-actions">
            {buttons}
        </div>
    </div>

</div>
{image_div}

## Abstract
{abstract}

## BibTex
```
{bibtex_str}
```
"""

    for entry in entries:
        citation_key = entry.get('ID')
        if not citation_key: continue

        filename = os.path.join(PUB_OUTPUT_DIR, f"{citation_key}.md")
        
        # Prepare Data
        title = clean_text(entry.get('title', 'Untitled'))
        authors = format_authors(entry)
        year = entry.get('year', 'N/A')
        venue = entry.get('journal') or entry.get('booktitle') or "Preprint"
        abstract = entry.get('abstract', 'No abstract available.')
        
        # --- GENERATE DESCRIPTION (Hybrid Method) ---
        # 1. Look for explicit description/note fields
        raw_desc = entry.get('description') or entry.get('note') or entry.get('annote')
        
        # 2. Fallback to truncated abstract
        if not raw_desc:
            clean_abs = clean_text(abstract)
            if clean_abs and clean_abs != 'No abstract available.':
                limit = 160
                raw_desc = clean_abs[:limit] + "..." if len(clean_abs) > limit else clean_abs
            else:
                raw_desc = ""
        
        # 3. Clean and escape for YAML
        description = clean_text(raw_desc).replace('"', '\\"')

        # --- GENERATE DATE ---
        # Prioritize explicit 'date' field in bibtex (e.g. 2023-05-12)
        pub_date = entry.get('date')
        
        # Fallback: Construct date from year and month
        if not pub_date:
            if year != 'N/A':
                # Attempt to extract month, default to January
                raw_month = entry.get('month', '01').lower()
                
                # Simple parsing for text months (jan, feb...)
                month_map = {
                    'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04', 'may': '05', 'jun': '06',
                    'jul': '07', 'aug': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
                }
                
                month = '01'
                if raw_month.isdigit():
                    month = raw_month.zfill(2)
                else:
                    for k, v in month_map.items():
                        if k in raw_month:
                            month = v
                            break
                
                pub_date = f"{year}-{month}-01"
            else:
                # Absolute fallback if no year is found
                pub_date = "1970-01-01"

        # Generate Buttons
        buttons = generate_buttons_html(entry)

        # Handle Image
        image_html = ""
        found_image = False
        for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
            possible_path = os.path.join(PUB_IMAGE_DIR_ABS, f"{citation_key}{ext}")
            if os.path.exists(possible_path):
                image_src = f"/{PUB_IMAGE_DIR_REL}/{citation_key}{ext}"
                image_html = f'<img src="{image_src}" alt="{citation_key}" class="pub-page-image" />'
                found_image = True
                break
        
        # Prepare BibTeX string safely
        db = bibtexparser.bibdatabase.BibDatabase()
        db.entries = [entry]
        bibtex_str = bibtexparser.dumps(db)
        
        # Format the content
        md_content = md_template.format(
            title=title,
            description=description,
            date=pub_date,
            venue=venue,
            year=year,
            authors=authors,
            buttons=buttons,
            image_class='has-image' if found_image else 'no-image',
            image_div=f'<div class="pub-image-container">{image_html}</div>' if found_image else '',
            abstract=abstract,
            bibtex_str=bibtex_str
        )
        
        # Write file only if content changed to avoid unnecessary rebuild loops
        write_file = True
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                if f.read().strip() == md_content.strip():
                    write_file = False
        
        if write_file:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(md_content)

def define_env(env):
    
    # 1. Generate pages immediately when environment loads
    create_publication_pages()

    @env.macro
    def generate_publication_table(bib_file=BIB_FILE):
        entries = load_bib_data(bib_file)
        if not entries:
            return f"<p style='color:red'>Error: Could not find {bib_file}</p>"

        # Table Header
        html = dedent("""
        <div class="table-container">
        <table class="neon-table">
            <thead>
                <tr>
                    <th width="10%">Year</th>
                    <th width="60%">Title & Authors</th>
                    <th width="15%">Venue</th>
                    <th width="15%">Links</th>
                </tr>
            </thead>
            <tbody>
        """)

        for entry in entries:
            title = clean_text(entry.get('title', 'Untitled'))
            authors = format_authors(entry)
            venue = entry.get('journal') or entry.get('booktitle') or "Preprint"
            year = entry.get('year', 'N/A')
            citation_key = entry.get('ID')

            # Generate Link Buttons
            links_html = generate_buttons_html(entry)
            
            # Create Link to the individual page
            page_link = f"/publications/{citation_key}/"

            # ADD ROW
            html += dedent(f"""
            <tr>
                <td class="year-cell">{year}</td>
                <td>
                    <div class="pub-title">
                        <a href="{page_link}" class="title-link">{title}</a>
                    </div>
                    <div class="pub-authors">{authors}</div>
                </td>
                <td class="venue-cell">{venue}</td>
                <td style="text-align: center;">
                    {links_html}
                </td>
            </tr>
            """)

        html += "</tbody></table></div>"
        return Markup(html)
    
    @env.macro
    def generate_talks_grid(folder="docs/talks"):
        talks = []
        if not os.path.exists(folder):
            return f"<p style='color:red'>Folder not found: {folder}</p>"

        for filename in os.listdir(folder):
            if filename.endswith(".md") and filename != "index.md":
                filepath = os.path.join(folder, filename)
                with open(filepath, encoding='utf-8') as f:
                    post = frontmatter.load(f)
                    if post.get('draft') is True: continue

                    talk_data = {
                        'title': post.get('title', 'Untitled'),
                        'date': post.get('date', datetime.date.min),
                        'short_conference_title': post.get('short_conference_title', 'Unknown Venue'),
                        'description': post.get('description', ''),
                        'url': filename.replace('.md', '/'), 
                    }
                    talks.append(talk_data)

        talks.sort(key=lambda x: x['date'], reverse=True)

        html = '<div class="bento-grid">'
        for talk in talks:
            date_str = talk['date']
            if isinstance(date_str, (datetime.date, datetime.datetime)):
                date_str = date_str.strftime("%b %Y")

            html += dedent(f"""
            <div class="bento-card" style="display: flex; flex-direction: column; justify-content: space-between; height: 100%;">
                <div>
                    <p style="opacity: 0.6; font-size: 0.85rem; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px;">
                        <span style="color: var(--neon-accent); font-weight: bold;">{date_str}</span> 
                        &nbsp;•&nbsp; {talk['short_conference_title']}
                    </p>
                    <h3 style="margin-top: 0; margin-bottom: 12px; font-size: 1.4rem; line-height: 1.3;">
                        {talk['title']}
                    </h3>
                    <p class="subtext" style="line-height: 1.6; margin-bottom: 1.5rem; font-size: 0.95rem;">
                        {talk['description']}
                    </p>
                </div>
                <a href="{talk['url']}" class="text-link" style="margin-top: auto;">View Talk&rarr;</a>
            </div>
            """)
        html += '</div>'
        return Markup(html)

    @env.macro
    def generate_projects_grid(folder="docs/projects"):
        projects = []
        if not os.path.exists(folder):
            return f"<p>Folder not found: {folder}</p>"

        for filename in os.listdir(folder):
            if filename.endswith(".md") and filename != "index.md":
                filepath = os.path.join(folder, filename)
                with open(filepath, encoding='utf-8') as f:
                    post = frontmatter.load(f)
                    if post.get('draft') is True: continue

                    projects.append({
                        'title': post.get('title', 'Untitled'),
                        'description': post.get('description', ''),
                        'url': filename.replace('.md', '/'),
                        'tags': post.get('tags', []),
                        'weight': post.get('weight', 0)
                    })

        projects.sort(key=lambda x: (x['weight'], x['title']), reverse=True)

        html = '<div class="bento-grid">'
        for p in projects:
            tags_html = ""
            for tag in p['tags'][:3]:
                tags_html += f'<span class="tech-tag">{tag}</span>'

            html += dedent(f"""
            <div class="bento-card" style="display: flex; flex-direction: column;">
                <h3 style="margin-top: 0; margin-bottom: 10px;">{p['title']}</h3>
                <div style="margin-bottom: 15px; display: flex; gap: 6px; flex-wrap: wrap;">
                    {tags_html}
                </div>
                <p class="subtext" style="flex-grow: 1; margin-bottom: 1.5rem;">
                    {p['description']}
                </p>
                <a href="{p['url']}" class="text-link" style="margin-top: auto;">View Project&rarr;</a>
            </div>
            """)
        html += '</div>'
        return Markup(html)

    @env.macro
    def generate_rotating_grid(folder="docs/quotes", interval=5000, keys=None, 
                               title="Highlights", icon="fa-solid fa-star", 
                               url="#", url_text="View All",
                               width=1, height=1, limit=5, order="random"):
        """
        Rotates through markdown files in a folder and subfolders. Includes Progress Bar and Hover-Pause.
        """
        
        if keys is None:
            keys = ['title', 'description'] # Default fallback

        items = []
        if not os.path.exists(folder):
            return dedent(f"""
            <div class='bento-card' style='grid-column: span {width}; grid-row: span {height};'>
                <p style='color: var(--neon-accent)'>
                    <strong>Tip:</strong> Create folder <code>{folder}</code> to see content!
                </p>
            </div>
            """)

        # Walk through files in folder and subfolders
        for root, dirs, files in os.walk(folder):
            for filename in files:
                if filename.endswith(".md") and filename != "index.md":
                    filepath = os.path.join(root, filename)
                    with open(filepath, encoding='utf-8') as f:
                        post = frontmatter.load(f)
                        
                        # Ignore drafts
                        if post.get('draft') is True: continue
                        
                        # Extract Data based on keys
                        main_text = ""
                        sub_text = ""
                        
                        # First key is the Headline
                        if len(keys) > 0:
                            val = post.get(keys[0], "Untitled")
                            main_text = str(val) if val else ""

                        # Subsequent keys are Description/Subtext
                        if len(keys) > 1:
                            sub_values = []
                            for k in keys[1:]:
                                val = post.get(k)
                                if val:
                                    if isinstance(val, list):
                                        val = ", ".join(str(v) for v in val)
                                    sub_values.append(str(val))
                            sub_text = " • ".join(sub_values)

                        # Extract Date
                        raw_date = post.get('date')
                        final_date = datetime.date.min
                        if isinstance(raw_date, (datetime.date, datetime.datetime)):
                            final_date = raw_date
                        elif isinstance(raw_date, str):
                            try:
                                final_date = datetime.datetime.strptime(raw_date, "%Y-%m-%d").date()
                            except ValueError:
                                pass

                        # Construct URL based on relative path from 'docs'
                        try:
                            # Safely get relative path from docs folder
                            rel_path = os.path.relpath(filepath, "docs")
                        except ValueError:
                            # Fallback if path logic fails
                            rel_path = filepath
                        
                        # Standard URL
                        item_url = "/" + rel_path.replace(os.sep, "/").replace(".md", "/")

                        # Special Handling for Blog Posts
                        path_segments = rel_path.split(os.sep)
                        if "posts" in path_segments:
                            try:
                                posts_idx = path_segments.index("posts")
                                base_blog_path = "/".join(path_segments[:posts_idx])
                                
                                # 1. Determine Slug (Title/Metadata Priority)
                                slug = post.get('slug')
                                if not slug and post.get('title'):
                                    slug = _slugify(post.get('title'))
                                
                                # Fallback: Filename
                                if not slug:
                                    if len(filename) > 10 and filename[4] == '-' and filename[7] == '-':
                                        slug = _slugify(filename[11:].replace(".md", ""))
                                    else:
                                        slug = _slugify(filename.replace(".md", ""))
                                
                                post_year, post_month, post_day = None, None, None

                                # Strategy A: Filename Date (Standard)
                                if len(filename) > 10 and filename[4] == '-' and filename[7] == '-':
                                    # Very basic check: 2023-01-01-...
                                    y, m, d = filename[0:4], filename[5:7], filename[8:10]
                                    if y.isdigit() and m.isdigit() and d.isdigit():
                                        post_year, post_month, post_day = y, m, d

                                # Strategy B: Frontmatter Date (Fallback)
                                if not post_year and isinstance(final_date, (datetime.date, datetime.datetime)):
                                    if final_date != datetime.date.min: # ensure it's not the default
                                        post_year = f"{final_date.year:04d}"
                                        post_month = f"{final_date.month:02d}"
                                        post_day = f"{final_date.day:02d}"

                                # Construct Blog URL if we have a date
                                if post_year and post_month and post_day:
                                    if base_blog_path:
                                        item_url = f"/{base_blog_path}/{post_year}/{post_month}/{post_day}/{slug}/"
                                    else:
                                        item_url = f"/{post_year}/{post_month}/{post_day}/{slug}/"
                            except Exception:
                                pass 

                        items.append({
                            'main': main_text,
                            'sub': sub_text,
                            'date': final_date,
                            'url': item_url
                        })

        # --- OPTIMIZATION & SORTING ---
        if order == "newest":
             items.sort(key=lambda x: x['date'], reverse=True)
        else:
            random.shuffle(items)
        
        if limit and limit > 0:
            items = items[:limit]

        if not items:
            return ""

        unique_id = f"rotator-{random.randint(1000, 9999)}"
        grid_style = f"grid-column: span {width}; grid-row: span {height};"

        # Logic to handle Icon:
        # 1. Fix missing base class (e.g. "mdi-file" -> "mdi mdi-file")
        if icon.startswith("mdi-") and " " not in icon:
            icon = f"mdi {icon}"

        # 2. Render as <i> if it looks like a class or raw HTML/SVG
        if icon.strip().startswith("<"):
             icon_html = f'<span class="card-header-icon">{icon}</span>' # Use span for raw SVG/Img
        elif " " in icon or icon.startswith(("fa-", "ai-", "bi-", "wi-", "mdi-", "ti-", "si-")):
             icon_html = f'<i class="{icon} card-header-icon"></i>'
        else:
             # 3. Fallback to <span> for emoji/text
             icon_html = f'<span class="card-header-icon">{icon}</span>'

        # --- HTML CONSTRUCTION ---
        html = dedent(f"""
        <div class="bento-card rotating-card" id="{unique_id}" style="{grid_style}">
            
            <div class="card-static-header">
                {icon_html}
                <span class="card-header-title">{title}</span>
            </div>

            <!-- PROGRESS BAR -->
            <div class="ticker-bar-container">
                <div class="ticker-bar" style="animation-duration: {interval}ms;"></div>
            </div>

            <div class="rotating-wrapper">
        """)

        for i, item in enumerate(items):
            active_class = "active" if i == 0 else ""
            
            html += dedent(f"""
            <div class="rotating-item {active_class}">
                <a href="{item['url']}" class="rotator-main-link">
                    <div class="rotator-main">{item['main']}</div>
                </a>
                <div class="rotator-sub">{item['sub']}</div>
            </div>
            """)

        html += dedent(f"""
            </div>
            
            <a href="{url}" class="text-link card-static-footer">
                {url_text} &rarr;
            </a>

        </div>
        """)

        # --- JS (SYNCED via Animation End) ---
        html += dedent(f"""
        <script>
        (function() {{
            const container = document.getElementById('{unique_id}');
            if (!container) return;
            
            const items = container.querySelectorAll('.rotating-item');
            const bar = container.querySelector('.ticker-bar');
            if (items.length < 2 || !bar) return;
            
            let currentIndex = 0;

            // Start the animation
            bar.classList.add('animate-progress');

            // When animation finishes, swap slides
            bar.addEventListener('animationend', () => {{
                // 1. Swap Classes
                items[currentIndex].classList.remove('active');
                
                let nextIndex;
                do {{ nextIndex = Math.floor(Math.random() * items.length); }} while (nextIndex === currentIndex);
                
                items[nextIndex].classList.add('active');
                currentIndex = nextIndex;

                // 2. Reset Animation (Force Reflow)
                bar.classList.remove('animate-progress');
                void bar.offsetWidth; // Trigger reflow
                bar.classList.add('animate-progress');
            }});
        }})();
        </script>
        """)

        return Markup(html)