---
title: Vasilis Tsilidis' personal site
description: Stay up to date with my research, projects and blog posts.
hide:
  - navigation
  - toc
---

<div class="bento-grid">

  <div class="bento-card wide-card">


    <div class="card-static-header card-header-icon">
      <i class="mdi mdi-hand-wave"></i>
      <span class="card-header-title"> Hello, I'm <span class="text-gradient">Vasilis Tsilidis</span>! </span>
    </div>


    <div class="card-content">
      <p>
        <strong>I enjoy learning about biological, psychological and social phenomena and investigating them through the lens of mathematics.</strong>
      </p>
      <br>              
      <a href="./assets/Vasilis_Tsilidis_CV.pdf" class="neon-button">Download CV</a>

    </div>
  </div>

  <div class="bento-card education-card">
        
    <div class="card-static-header">
        <i class="fa-solid fa-graduation-cap card-header-icon"></i>
        <span class="card-header-title">Education</span>
    </div>
    
    <div class="timeline">

      <div class="timeline-item">
        <span class="date">2023 - present</span>
        <h3>PhD in Mathematical Modelling</h3>
        <strong>University of Patras</strong>
      </div>

      <div class="timeline-item">
        <span class="date">2019 - 2021</span>
        <h3>MSc in Applied Mathematics</h3>
        <strong>Hellenic Open University</strong>
        <p>Thesis: <a href="https://apothesis.eap.gr/archive/item/75362?lang=en">Mathematical Modelling of Immune Response in Breast Cancer</a></p>
      </div>

      <div class="timeline-item">
        <span class="date">2013 - 2018</span>
        <h3>BSc in Mathematics</h3>
        <strong>National and Kapodistrian University of Athens</strong>
      </div>

    </div>
  </div>

<div class="bento-card">

    <div class="card-static-header card-header-icon">
      <i class="fa-solid fa-paper-plane"></i>
      <span class="card-header-title"> Let's Connect </span>
    </div>
    
    <p class="subtext">Find me on social media.</p>

    <div class="social-container">
      
      <a href="mailto:vtsilidis@upatras.gr" class="social-btn" title="Email">
        <i class="fa-solid fa-envelope"></i>
      </a>
      
      <a href="https://www.linkedin.com/in/vasilis-tsilidis" class="social-btn" title="LinkedIn">
        <i class="fa-brands fa-linkedin-in"></i>
      </a>

      <a href="https://scholar.google.com/citations?hl=en&user=3qaGBDkAAAAJ" class="social-btn" title="Google Scholar">
        <i class="ai ai-google-scholar"></i>
      </a>

      <a href="https://github.com/TsilidisV" class="social-btn" title="GitHub">
        <i class="fa-brands fa-github"></i>
      </a>

      <a href="https://orcid.org/0000-0001-5868-4984" class="social-btn" title="ORCID">
        <i class="ai ai-orcid"></i>
      </a>

      <a href="https://www.researchgate.net/profile/Vasilis_Tsilidis" class="social-btn" title="ResearchGate">
        <i class="ai ai-researchgate"></i>
      </a>

    </div>
  </div>

  <!-- Talks: Tall Card, pulling 'title' and 'short_conference_title' -->
  {{ generate_rotating_grid(
      folder="docs/projects",
      keys=['title', 'description'],
      title="Projects",
      icon="fa-solid fa-diagram-project",
      url="/projects/",
      url_text="View Projects",
      width=1,
      height=1
  ) }}

  <!-- Talks: Tall Card, pulling 'title' and 'short_conference_title' -->
  {{ generate_rotating_grid(
      folder="docs/publications",
      keys=['title', 'description'],
      title="Publications",
      icon="mdi mdi-file-document",
      url="/publications/",
      url_text="View Publications",
      order="newest",
      limit=5,
      width=2,
      height=1
  ) }}


  <!-- Talks: Tall Card, pulling 'title' and 'short_conference_title' -->
  {{ generate_rotating_grid(
      folder="docs/blog/posts",
      keys=['title', 'description'],
      title="Blog",
      icon="fa-solid fa-pen-nib",
      url="/blog/",
      url_text="View Blog",
      order="newest",
      limit=5,
      width=1,
      height=2
  ) }}



  <!-- Talks: Tall Card, pulling 'title' and 'short_conference_title' -->
  {{ generate_rotating_grid(
      folder="docs/talks",
      keys=['title', 'description'],
      title="Talks",
      icon="fa-solid fa-microphone-lines",
      url="/talks/",
      url_text="View Talks",
      width=2,
      height=1
  ) }}



</div>