# Personal Research Portfolio 🚀

A modern, automated personal website built for researchers and developers. It moves beyond standard static themes by integrating dynamic content generation, interactive UI components, and a custom "Neon Glassmorphism" aesthetic.

## ✨ Key Features

### 1. Dynamic Bibliography 📚

No more manual HTML updates. A custom Python pipeline (`main.py`) parses a standard `publications.bib` file during the build process to automatically generate:

* A filterable, sortable index of all publications.  
* **Individual landing pages** for every paper, complete with abstracts, citation buttons (PDF, BibTeX, ArXiv), and venue details.

### 2. Rotating Bento Grids 🍱

A fully interactive grid system designed to surface buried content.

* **Smart Rotation:** Content cards rotate through your projects or blog posts automatically.  
* **UX Polished:** Includes a progress bar ticker and **pauses on hover** for readability.  
* **Deep Linking:** Cards automatically link to specific project pages or blog posts (with correct URL slugification).

### 3. "Neon Glass" Theme 🎨

A comprehensive CSS override of the standard MkDocs Material theme (extra.css):

* **Glassmorphism:** Translucent cards with backdrop filters and delicate borders.  
* **Neon Accents:** A purple-to-cyan gradient system used for text, buttons, and shadows.  
* **Responsive:** Fluid layouts that stack gracefully on mobile devices.

## 🛠️ The Tech Stack

This project treats the website as an application, not just a document collection.

| Component | Technology | Description |
| :---- | :---- | :---- |
| **Core** | **MkDocs Material** | The fastest, most accessible static site generator foundation. |
| **Logic** | **Python (Jinja2)** | Custom main.py hooks into the build to generate dynamic HTML and Markdown. |
| **Data** | **BibTeX / YAML** | Content is managed via standard academic formats (.bib) and Frontmatter. |
| **Styling** | **CSS3** | Advanced CSS for animations, gradients, and layout control. |
| **Deploy** | **GitHub Actions** | Automated CI/CD using uv for lightning-fast builds. |

## 🚀 How to Run Locally

1. Clone the repository:
```bash 
git clone https://github.com/TsilidisV/TsilidisV.github.io.git
cd TsilidisV.github.io
```

2. Install dependencies (using uv is recommended): 
```bash
pip install uv  
uv pip install \-r requirements.txt
```

3. Serve the site:
```bash  
mkdocs serve
```

The site will be available at http://127.0.0.1:8000/.


## **📂 Project Structure**
```
.  
├── docs/  
│   ├── assets/             # Images and the master publications.bib  
│   ├── blog/               # Blog posts  
│   ├── projects/           # Markdown files for individual projects  
│   ├── publications/       # (Generated automatically by main.py)  
│   └── index.md            # Homepage  
├── extra.css               # The "Neon Glass" theme definitions  
├── main.py                 # The Python build engine & Macro logic  
├── mkdocs.yml              # Configuration  
└── requirements.txt        # Python dependencies
```
## 🤝 Contributing

Feel free to fork this repository and use it as a template for your own portfolio! If you find bugs in the `main.py` logic or CSS, pull requests are welcome.  
<p align="center">  
<span style="opacity: 0.6"\>Built with 💜 using Python & MkDocs<span\>  
<p\>