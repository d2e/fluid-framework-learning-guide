import os
import re
import json
import subprocess
from bs4 import BeautifulSoup

MD_PATH = "/Users/dhiraj.thakur/project/FluidFramework/learning.md"
OUT_PATH = "/Users/dhiraj.thakur/project/FluidFramework/learning.html"
RAW_HTML_PATH = "/tmp/raw_learning.html"

# Run pandoc with wrap=none
print("1. Running pandoc with --wrap=none...")
cmd = ["pandoc", MD_PATH, "-f", "gfm", "-t", "html5", "--wrap=none", "-o", RAW_HTML_PATH]
subprocess.run(cmd, check=True)

with open(RAW_HTML_PATH, "r", encoding="utf-8") as f:
    raw_html = f.read()

print(f"Loaded raw HTML ({len(raw_html)} bytes)")

soup = BeautifulSoup(raw_html, "html.parser")

CATEGORIES = [
    {
        "id": "cat-overview",
        "title": "Architecture Overview & Tooling",
        "badge": "Overview",
        "icon": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"></polygon></svg>',
        "item_ids": ["1-repository-layout", "2-ff-oce-on-call-agent"]
    },
    {
        "id": "cat-routerlicious",
        "title": "Routerlicious & Ordering Service",
        "badge": "Routerlicious",
        "icon": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect><rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect><line x1="6" y1="6" x2="6.01" y2="6"></line><line x1="6" y1="18" x2="6.01" y2="18"></line></svg>',
        "item_ids": [
            "3-routerlicious-server-architecture",
            "4-op-flow-end-to-end",
            "5-kafka-messaging-backpressure-and-scaling",
            "6-scriptorium-vs-scribe",
            "7-total-order-broadcast-tob",
            "8-why-git-for-snapshots",
            "9-how-a-new-user-joins-an-existing-session",
            "17-document-router--per-document-partitioning-in-deli"
        ]
    },
    {
        "id": "cat-observability",
        "title": "Observability & Telemetry",
        "badge": "Telemetry",
        "icon": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>',
        "item_ids": ["10-observability-architecture"]
    },
    {
        "id": "cat-client-dds",
        "title": "Client Runtime & DDS Core",
        "badge": "Runtime & DDS",
        "icon": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="4" width="16" height="16" rx="2" ry="2"></rect><rect x="9" y="9" width="6" height="6"></rect><line x1="9" y1="1" x2="9" y2="4"></line><line x1="15" y1="1" x2="15" y2="4"></line><line x1="9" y1="20" x2="9" y2="23"></line><line x1="15" y1="20" x2="15" y2="23"></line><line x1="20" y1="9" x2="23" y2="9"></line><line x1="20" y1="14" x2="23" y2="14"></line><line x1="1" y1="9" x2="4" y2="9"></line><line x1="1" y1="14" x2="4" y2="14"></line></svg>',
        "item_ids": [
            "11-dds-architecture",
            "12-collaborative-editing--sequence-numbers-walkthrough",
            "13-data-corruption-scenarios",
            "14-op-batching-compression-and-chunking",
            "18-signals-vs-ops",
            "19-noop-messages-and-msn-advancement",
            "20-container-lifecycle--detached--attaching--attached"
        ]
    },
    {
        "id": "cat-summaries-gc",
        "title": "Summaries & Garbage Collection",
        "badge": "Summaries & GC",
        "icon": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>',
        "item_ids": [
            "15-summarizer-client-election",
            "16-incremental-summaries",
            "21-garbage-collection-lifecycle"
        ]
    },
    {
        "id": "cat-security-ops",
        "title": "Security & Local Dev",
        "badge": "Security & Dev",
        "icon": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>',
        "item_ids": [
            "22-auth-and-token-flow-riddler",
            "23-local-development--tinylicious-and-docker-compose"
        ]
    },
    {
        "id": "cat-fluid2",
        "title": "Modern Fluid 2.x Architecture",
        "badge": "Fluid 2.x",
        "icon": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 2 7 12 12 22 7 12 2"></polygon><polyline points="2 17 12 22 22 17"></polyline><polyline points="2 12 12 17 22 12"></polyline></svg>',
        "item_ids": [
            "24-recent-upstream-fluid-2x-architecture--api-evolution"
        ]
    },
    {
        "id": "cat-interview",
        "title": "Interview Guide & Strategies",
        "badge": "Interview Script",
        "icon": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path><circle cx="9" cy="10" r="1"></circle><circle cx="12" cy="10" r="1"></circle><circle cx="15" cy="10" r="1"></circle></svg>',
        "item_ids": [
            "25-1-hour-deep-dive-technical-interview-script-director--distinguished-engineer"
        ]
    },
    {
        "id": "cat-reference",
        "title": "File Reference & Index",
        "badge": "Reference",
        "icon": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>',
        "item_ids": [
            "key-file-index",
            "updated-key-file-index"
        ]
    }
]

item_to_cat = {}
for cat in CATEGORIES:
    for item_id in cat["item_ids"]:
        item_to_cat[item_id] = cat

# 1. Transform tables
for tbl in soup.find_all('table'):
    wrapper = soup.new_tag('div', **{'class': 'table-responsive'})
    tbl.wrap(wrapper)

# 2. Transform div.sourceCode
for div in soup.find_all('div', class_='sourceCode'):
    pre = div.find('pre')
    classes = pre.get('class', []) if pre else []
    lang = 'CODE'
    for c in classes:
        if c != 'sourceCode':
            lang = c.upper()
            break
    if lang == 'TS': lang = 'TYPESCRIPT'
    if lang == 'SH': lang = 'BASH'
    
    container = soup.new_tag('div', **{'class': 'code-container', 'data-type': lang})
    header = soup.new_tag('div', **{'class': 'code-header'})
    badge = soup.new_tag('span', **{'class': f'code-badge badge-{lang.lower()}'})
    badge.string = lang
    header.append(badge)
    
    copy_btn = soup.new_tag('button', **{'class': 'copy-btn', 'onclick': 'copySnippet(this)', 'aria-label': 'Copy code', 'title': 'Copy code'})
    copy_btn.append(BeautifulSoup('<svg class="icon-copy" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg><span class="copy-label">Copy</span>', 'html.parser'))
    header.append(copy_btn)
    
    div.wrap(container)
    div.insert_before(header)
    div.unwrap()

# 3. Transform standalone pre
for pre in soup.find_all('pre'):
    if pre.find_parent('div', class_='code-container'):
        continue
    text = pre.get_text()
    if '├──' in text or '└──' in text:
        lang = 'DIRECTORY TREE'
        pre['class'] = pre.get('class', []) + ['ascii-diagram', 'tree-diagram']
    elif any(sym in text for sym in ['▼', '▲', '┌', '└', '──►', '├', '│', '→', '←', '─', '═']):
        lang = 'ARCHITECTURE DIAGRAM'
        pre['class'] = pre.get('class', []) + ['ascii-diagram', 'flow-diagram']
    elif '{' in text and '}' in text and '"' in text:
        lang = 'JSON'
        pre['class'] = pre.get('class', []) + ['code-json']
    else:
        lang = 'REFERENCE'
        pre['class'] = pre.get('class', []) + ['code-snippet']
        
    container = soup.new_tag('div', **{'class': 'code-container', 'data-type': lang})
    header = soup.new_tag('div', **{'class': 'code-header'})
    badge = soup.new_tag('span', **{'class': f'code-badge badge-{lang.lower().replace(" ", "-")}'})
    badge.string = lang
    header.append(badge)
    
    copy_btn = soup.new_tag('button', **{'class': 'copy-btn', 'onclick': 'copySnippet(this)', 'aria-label': 'Copy snippet', 'title': 'Copy snippet'})
    copy_btn.append(BeautifulSoup('<svg class="icon-copy" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg><span class="copy-label">Copy</span>', 'html.parser'))
    header.append(copy_btn)
    
    pre.wrap(container)
    pre.insert_before(header)

# 4. Transform blockquotes into styled callouts
for bq in soup.find_all('blockquote'):
    text = bq.get_text().strip()
    callout_type = "callout-info"
    callout_icon = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>'
    callout_title = "Architectural Note"
    
    if "Critical:" in text or "WARNING" in text:
        callout_type = "callout-warning"
        callout_icon = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>'
        callout_title = "Critical Requirement"
    elif "Captured from" in text:
        callout_type = "callout-meta"
        callout_icon = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>'
        callout_title = "Session Provenance"
    elif "The service must write" in text:
        callout_type = "callout-quote"
        callout_icon = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 21c3 0 7-1 7-8V5c0-1.25-.756-2.017-2-2H4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2 1 0 1 0 1 1v1c0 1-1 2-2 2s-1 .008-1 1.031V20c0 1 0 1 1 1z"></path><path d="M15 21c3 0 7-1 7-8V5c0-1.25-.757-2.017-2-2h-4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2 1 0 1 0 1 1v1c0 1-1 2-2 2s-1 .008-1 1.031V20c0 1 0 1 1 1z"></path></svg>'
        callout_title = "Service Summary Rationale"
    elif text.startswith('"') or text.startswith('“') or "Let's trace" in text or "When building" in text or "A natural question" in text:
        callout_type = "callout-quote"
        callout_icon = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path><polyline points="8 10 12 14 16 10"></polyline></svg>'
        callout_title = "Verbatim Interview Delivery (Spoken Script)"

    callout_box = soup.new_tag('div', **{'class': f'callout {callout_type}'})
    callout_header = soup.new_tag('div', **{'class': 'callout-header'})
    callout_header.append(BeautifulSoup(callout_icon, 'html.parser'))
    title_span = soup.new_tag('span', **{'class': 'callout-title'})
    title_span.string = callout_title
    callout_header.append(title_span)
    
    callout_body = soup.new_tag('div', **{'class': 'callout-body'})
    for child in list(bq.children):
        callout_body.append(child)
        
    callout_box.append(callout_header)
    callout_box.append(callout_body)
    bq.replace_with(callout_box)

# 5. Add permalink anchors to headings
for h in soup.find_all(['h2', 'h3', 'h4', 'h5']):
    hid = h.get('id', '')
    if not hid:
        continue
    anchor = soup.new_tag('a', **{'class': 'heading-anchor', 'href': f'#{hid}', 'aria-label': f'Permalink to {h.get_text().strip()}'})
    anchor.string = '#'
    h.append(anchor)

# 6. Extract search items
search_index = []
for h in soup.find_all(['h2', 'h3', 'h4']):
    hid = h.get('id', '')
    if not hid or hid == 'table-of-contents':
        continue
    htext = ' '.join(h.get_text().replace('#', '').split())
    excerpt = ""
    curr = h.next_sibling
    while curr and len(excerpt) < 180:
        if getattr(curr, 'name', None) in ['h2', 'h3', 'h4']:
            break
        if hasattr(curr, 'get_text'):
            excerpt += " " + ' '.join(curr.get_text().split())
        curr = curr.next_sibling
    excerpt = excerpt.strip()[:180]
    
    cat = item_to_cat.get(hid, None)
    cat_name = cat["title"] if cat else "Fluid Framework Core"
    
    search_index.append({
        "id": hid,
        "title": htext,
        "category": cat_name,
        "level": h.name,
        "excerpt": excerpt
    })

# Read official SVGs
def read_clean_svg(path):
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        svg_raw = f.read()
    svg_clean = re.sub(r'<\?xml[^>]*\?>', '', svg_raw)
    svg_clean = re.sub(r'<!DOCTYPE[^>]*>', '', svg_clean).strip()
    return svg_clean

svg_routerlicious = read_clean_svg("/Users/dhiraj.thakur/project/FluidFramework/server/routerlicious/docs/Routerlicious-Architecture.svg")
svg_routerlicious_hld = read_clean_svg("/Users/dhiraj.thakur/project/FluidFramework/server/routerlicious/docs/Routerlicious-HLD.svg")
svg_connection_states = read_clean_svg("/Users/dhiraj.thakur/project/FluidFramework/docs/docs/build/images/ConnectionStates.svg")
svg_sync_states = read_clean_svg("/Users/dhiraj.thakur/project/FluidFramework/docs/docs/build/images/SynchronizationStates.svg")

# 7. Structure chapters
body_html = str(soup)
parts = re.split(r'(?=<h2\s+id=)', body_html)
intro_html = parts[0]
chapter_sections = []

total_items = sum(len(c["item_ids"]) for c in CATEGORIES)
total_modules = len(CATEGORIES)

toc_grid_html = f'''<div class="toc-dashboard" id="table-of-contents">
  <div class="toc-dashboard-header">
    <div class="toc-dashboard-title-row">
      <h2>Architecture & Learning Modules Dashboard</h2>
      <span class="toc-badge-total">{total_items} Chapters &bull; {total_modules} Modules</span>
    </div>
    <p>Explore the end-to-end architecture of Fluid Framework, Routerlicious ordering pipeline, DDS distributed state, modern Fluid 2.x, and the 1-hour executive interview guide.</p>
  </div>
  <div class="toc-grid">
'''

for cat in CATEGORIES:
    toc_grid_html += f'''
    <div class="toc-card" data-cat="{cat['id']}">
      <div class="toc-card-header">
        <span class="toc-card-icon">{cat['icon']}</span>
        <h3>{cat['title']}</h3>
      </div>
      <ul class="toc-card-list">
    '''
    for item_id in cat["item_ids"]:
        item_title = item_id.replace('-', ' ').title()
        for s in search_index:
            if s["id"] == item_id:
                item_title = s["title"]
                break
        toc_grid_html += f'<li><a href="#{item_id}">{item_title}</a></li>'
    toc_grid_html += '''
      </ul>
    </div>
    '''
toc_grid_html += '''
  </div>
</div>
'''

for part in parts[1:]:
    m = re.search(r'<h2\s+id="([^"]+)"[^>]*>(.*?)</h2>', part, re.DOTALL)
    if not m:
        chapter_sections.append(part)
        continue
    sec_id = m.group(1)
    
    if sec_id == 'table-of-contents':
        chapter_sections.append(toc_grid_html)
        continue
    
    cat = item_to_cat.get(sec_id, {
        "id": "cat-general",
        "title": "Fluid Core",
        "badge": "Core"
    })
    
    plain_text = re.sub('<[^<]+?>', '', part)
    word_count = len(plain_text.split())
    read_mins = max(1, round(word_count / 200))
    
    # Extract H3 subsections for jump chips
    h3_matches = re.findall(r'<h3\s+id="([^"]+)"[^>]*>(.*?)</h3>', part, re.DOTALL)
    jump_pills_html = ""
    if h3_matches:
        jump_pills_html = '<div class="section-jump-chips">'
        for h3_id, h3_text in h3_matches[:7]:
            clean_h3 = ' '.join(re.sub('<[^<]+?>', '', h3_text).replace('#', '').split())
            jump_pills_html += f'<a href="#{h3_id}" class="jump-chip">{clean_h3}</a>'
        if len(h3_matches) > 7:
            jump_pills_html += f'<span class="jump-chip-more">+{len(h3_matches)-7} more</span>'
        jump_pills_html += '</div>'
    
    # Check if we should inject official SVG graphics
    extra_svg_html = ""
    if sec_id == "3-routerlicious-server-architecture":
        cards = []
        if svg_routerlicious_hld:
            cards.append(f'''
        <details class="official-graphic-card" open>
          <summary class="official-graphic-summary">
            <div class="summary-left">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline></svg>
              <span>Routerlicious High-Level Design (HLD) — 4-Section Architectural Flow</span>
            </div>
            <span class="graphic-badge" style="background: rgba(16, 185, 129, 0.2); color: #10b981;">Complete Op &amp; Summary Flow</span>
          </summary>
          <div class="svg-diagram-wrapper">
            <div class="svg-diagram-content">
              {svg_routerlicious_hld}
            </div>
            <div class="svg-diagram-footer" style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
              <span>Source: <code>server/routerlicious/docs/Routerlicious-HLD.excalidraw</code></span>
              <div style="display: flex; gap: 14px;">
                <a href="routerlicious-hld.html" target="_blank" style="color: var(--primary); text-decoration: none; font-weight: 600;">Standalone View ↗</a>
                <a href="Routerlicious-HLD.excalidraw" download style="color: var(--text-muted); text-decoration: none;">Download .excalidraw</a>
              </div>
            </div>
          </div>
        </details>
            ''')
        if svg_routerlicious:
            cards.append(f'''
        <details class="official-graphic-card" style="margin-top: 20px;">
          <summary class="official-graphic-summary">
            <div class="summary-left">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline></svg>
              <span>Official Routerlicious Visual Architecture Diagram (Visio SVG)</span>
            </div>
            <span class="graphic-badge">Interactive Repository Asset</span>
          </summary>
          <div class="svg-diagram-wrapper">
            <div class="svg-diagram-content">
              {svg_routerlicious}
            </div>
            <div class="svg-diagram-footer">
              <span>Source: <code>server/routerlicious/docs/Routerlicious-Architecture.svg</code></span>
            </div>
          </div>
        </details>
            ''')
        extra_svg_html = '\n'.join(cards)
    elif sec_id == "20-container-lifecycle--detached--attaching--attached" and svg_connection_states:
        extra_svg_html = f'''
        <details class="official-graphic-card" open>
          <summary class="official-graphic-summary">
            <div class="summary-left">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline></svg>
              <span>Connection & Synchronization States Architecture</span>
            </div>
            <span class="graphic-badge">State Machine SVG</span>
          </summary>
          <div class="svg-diagram-wrapper">
            <div class="svg-diagram-content">
              {svg_connection_states}
            </div>
            {f'<div class="svg-diagram-content" style="margin-top: 20px; border-top: 1px solid var(--border-subtle); padding-top: 20px;">{svg_sync_states}</div>' if svg_sync_states else ''}
            <div class="svg-diagram-footer">
              <span>Source: <code>docs/docs/build/images/ConnectionStates.svg</code></span>
            </div>
          </div>
        </details>
        '''

    wrapped = f'''
    <section class="guide-chapter" id="{sec_id}" data-category="{cat['id']}">
      <div class="chapter-banner">
        <div class="banner-top">
          <span class="category-pill">{cat['badge']}</span>
          <span class="reading-meta">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
            {read_mins} min read &bull; {word_count} words
          </span>
        </div>
        {jump_pills_html}
      </div>
      <div class="chapter-body">
        {extra_svg_html}
        {part}
      </div>
    </section>
    '''
    chapter_sections.append(wrapped)

assembled_body = intro_html + "\n" + "\n".join(chapter_sections)

# Build Sidebar HTML
sidebar_categories_html = f'''
<div class="sidebar-item toc-special-link" style="margin-bottom: 12px;">
  <a href="#table-of-contents" class="sidebar-link special-toc-btn">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>
    <span>Module Dashboard (TOC)</span>
  </a>
</div>
'''

for cat in CATEGORIES:
    items_html = ""
    for item_id in cat["item_ids"]:
        item_title = item_id.replace('-', ' ').title()
        for s in search_index:
            if s["id"] == item_id:
                item_title = s["title"]
                break
        items_html += f'''
        <li class="sidebar-item" data-id="{item_id}">
          <a href="#{item_id}" class="sidebar-link">
            <span class="sidebar-link-bullet"></span>
            <span class="sidebar-link-text">{item_title}</span>
          </a>
        </li>
        '''
    
    sidebar_categories_html += f'''
    <div class="sidebar-group" data-group="{cat['id']}">
      <button class="sidebar-group-header" onclick="toggleSidebarGroup(this)">
        <span class="sidebar-group-icon">{cat['icon']}</span>
        <span class="sidebar-group-title">{cat['title']}</span>
        <span class="sidebar-group-badge">{len(cat['item_ids'])}</span>
        <svg class="sidebar-group-chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"></polyline></svg>
      </button>
      <ul class="sidebar-group-items">
        {items_html}
      </ul>
    </div>
    '''

print("Generating final learning.html...")

MASTER_HTML = f'''<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Fluid Framework & Routerlicious — Developer Architecture & Learning Guide</title>
  <meta name="description" content="In-depth developer reference and architectural learning guide for Fluid Framework: Routerlicious, Total Order Broadcast (ToB), Kafka pipelines, DDSes, Scriptorium vs Scribe, GC, and Telemetry.">
  <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%2338bdf8'><path d='M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5'/></svg>">
  
  <style>
    /* CSS Variables & Modern Palette */
    :root {{
      --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      --font-mono: ui-monospace, "SF Mono", Monaco, "Cascadia Code", "Source Code Pro", Menlo, Consolas, "Liberation Mono", monospace;
      
      --bg-base: #0b0f19;
      --bg-surface: #111827;
      --bg-surface-elevated: #1f2937;
      --bg-surface-hover: #263345;
      --bg-code: #070a12;
      
      --border-subtle: rgba(255, 255, 255, 0.08);
      --border-medium: rgba(255, 255, 255, 0.16);
      --border-accent: #38bdf8;
      
      --text-main: #f3f4f6;
      --text-muted: #9ca3af;
      --text-dim: #6b7280;
      
      --primary: #38bdf8;
      --primary-hover: #0ea5e9;
      --primary-glow: rgba(56, 189, 248, 0.15);
      
      --accent-purple: #c084fc;
      --accent-emerald: #34d399;
      --accent-amber: #fbbf24;
      --accent-rose: #f43f5e;
      
      --sidebar-width: 330px;
      --header-height: 64px;
      --content-max-width: 1120px;
      --radius-sm: 6px;
      --radius-md: 10px;
      --radius-lg: 16px;
      --shadow-lg: 0 10px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.5);
    }}

    [data-theme="light"] {{
      --bg-base: #f8fafc;
      --bg-surface: #ffffff;
      --bg-surface-elevated: #f1f5f9;
      --bg-surface-hover: #e2e8f0;
      --bg-code: #0f172a;
      
      --border-subtle: rgba(0, 0, 0, 0.08);
      --border-medium: rgba(0, 0, 0, 0.15);
      --border-accent: #0284c7;
      
      --text-main: #0f172a;
      --text-muted: #475569;
      --text-dim: #64748b;
      
      --primary: #0284c7;
      --primary-hover: #0369a1;
      --primary-glow: rgba(2, 132, 199, 0.12);
      
      --accent-purple: #9333ea;
      --accent-emerald: #059669;
      --accent-amber: #d97706;
      --accent-rose: #e11d48;
      
      --shadow-lg: 0 10px 25px -5px rgba(0, 0, 0, 0.08), 0 8px 10px -6px rgba(0, 0, 0, 0.04);
    }}

    *, *::before, *::after {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}

    html {{
      scroll-behavior: smooth;
      scroll-padding-top: calc(var(--header-height) + 24px);
      font-size: 15px;
    }}

    body {{
      font-family: var(--font-sans);
      background-color: var(--bg-base);
      color: var(--text-main);
      line-height: 1.68;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      -webkit-font-smoothing: antialiased;
    }}

    /* Top Reading Progress Bar */
    #reading-progress {{
      position: fixed;
      top: 0;
      left: 0;
      height: 3px;
      width: 0%;
      background: linear-gradient(90deg, #38bdf8, #818cf8, #c084fc);
      z-index: 1000;
      transition: width 0.1s ease-out;
    }}

    /* Header */
    header.site-header {{
      position: sticky;
      top: 0;
      height: var(--header-height);
      background: rgba(17, 24, 39, 0.88);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--border-subtle);
      z-index: 900;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 24px;
    }}

    [data-theme="light"] header.site-header {{
      background: rgba(255, 255, 255, 0.9);
    }}

    .header-left {{
      display: flex;
      align-items: center;
      gap: 16px;
    }}

    .btn-icon {{
      background: none;
      border: 1px solid var(--border-subtle);
      color: var(--text-muted);
      border-radius: var(--radius-sm);
      width: 36px;
      height: 36px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: all 0.2s;
    }}

    .btn-icon:hover {{
      background: var(--bg-surface-hover);
      color: var(--text-main);
      border-color: var(--border-medium);
    }}

    .brand-logo {{
      display: flex;
      align-items: center;
      gap: 12px;
      text-decoration: none;
      color: var(--text-main);
      font-weight: 700;
      font-size: 1.15rem;
      letter-spacing: -0.01em;
    }}

    .brand-badge {{
      font-size: 0.72rem;
      font-weight: 600;
      padding: 2px 8px;
      border-radius: 999px;
      background: var(--primary-glow);
      color: var(--primary);
      border: 1px solid rgba(56, 189, 248, 0.3);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}

    .header-actions {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}

    .search-trigger {{
      display: flex;
      align-items: center;
      gap: 10px;
      background: var(--bg-surface-elevated);
      border: 1px solid var(--border-subtle);
      color: var(--text-muted);
      padding: 6px 14px;
      border-radius: var(--radius-md);
      font-size: 0.88rem;
      cursor: pointer;
      transition: all 0.2s;
      min-width: 250px;
    }}

    .search-trigger:hover {{
      border-color: var(--primary);
      color: var(--text-main);
      box-shadow: 0 0 10px var(--primary-glow);
    }}

    .kbd-shortcut {{
      font-family: var(--font-mono);
      font-size: 0.75rem;
      padding: 2px 6px;
      background: var(--bg-base);
      border: 1px solid var(--border-subtle);
      border-radius: 4px;
      margin-left: auto;
      color: var(--text-dim);
    }}

    /* Main App Layout */
    .app-layout {{
      display: flex;
      flex: 1;
    }}

    /* Left Sidebar */
    aside.sidebar {{
      width: var(--sidebar-width);
      position: sticky;
      top: var(--header-height);
      height: calc(100vh - var(--header-height));
      overflow-y: auto;
      background: var(--bg-surface);
      border-right: 1px solid var(--border-subtle);
      padding: 20px 16px;
      flex-shrink: 0;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }}

    aside.sidebar::-webkit-scrollbar {{
      width: 5px;
    }}
    aside.sidebar::-webkit-scrollbar-thumb {{
      background: var(--border-subtle);
      border-radius: 3px;
    }}

    .sidebar-filter-wrapper {{
      position: relative;
    }}

    .sidebar-filter-input {{
      width: 100%;
      background: var(--bg-base);
      border: 1px solid var(--border-subtle);
      color: var(--text-main);
      padding: 8px 12px 8px 32px;
      border-radius: var(--radius-sm);
      font-size: 0.85rem;
      outline: none;
      transition: border-color 0.2s;
    }}

    .sidebar-filter-input:focus {{
      border-color: var(--primary);
    }}

    .sidebar-filter-icon {{
      position: absolute;
      left: 10px;
      top: 50%;
      transform: translateY(-50%);
      color: var(--text-dim);
      pointer-events: none;
    }}

    .sidebar-groups {{
      display: flex;
      flex-direction: column;
      gap: 12px;
    }}

    .sidebar-group {{
      display: flex;
      flex-direction: column;
      gap: 4px;
    }}

    .sidebar-group-header {{
      display: flex;
      align-items: center;
      gap: 10px;
      width: 100%;
      background: none;
      border: none;
      color: var(--text-muted);
      font-size: 0.8rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      padding: 8px 10px;
      border-radius: var(--radius-sm);
      cursor: pointer;
      text-align: left;
      transition: all 0.2s;
    }}

    .sidebar-group-header:hover {{
      color: var(--text-main);
      background: var(--bg-surface-elevated);
    }}

    .sidebar-group-icon {{
      color: var(--primary);
      display: flex;
      align-items: center;
    }}

    .sidebar-group-title {{
      flex: 1;
    }}

    .sidebar-group-badge {{
      font-size: 0.7rem;
      padding: 1px 6px;
      border-radius: 999px;
      background: var(--bg-base);
      color: var(--text-dim);
    }}

    .sidebar-group-chevron {{
      transition: transform 0.2s ease;
    }}

    .sidebar-group.collapsed .sidebar-group-chevron {{
      transform: rotate(-90deg);
    }}

    .sidebar-group.collapsed .sidebar-group-items {{
      display: none;
    }}

    .sidebar-group-items {{
      list-style: none;
      display: flex;
      flex-direction: column;
      gap: 2px;
      padding-left: 8px;
    }}

    .sidebar-item {{
      margin: 0;
    }}

    .sidebar-link {{
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 6px 12px;
      border-radius: var(--radius-sm);
      color: var(--text-muted);
      text-decoration: none;
      font-size: 0.88rem;
      transition: all 0.15s ease;
      line-height: 1.35;
      border-left: 2px solid transparent;
    }}

    .sidebar-link:hover {{
      color: var(--text-main);
      background: var(--bg-surface-hover);
    }}

    .sidebar-link.active {{
      color: var(--primary);
      font-weight: 600;
      background: var(--primary-glow);
      border-left-color: var(--primary);
    }}

    .special-toc-btn {{
      background: var(--bg-surface-elevated);
      color: var(--primary);
      font-weight: 600;
      border: 1px solid var(--border-subtle);
    }}

    .special-toc-btn:hover {{
      background: var(--bg-surface-hover);
      border-color: var(--primary);
    }}

    .sidebar-link-bullet {{
      width: 4px;
      height: 4px;
      border-radius: 50%;
      background: var(--text-dim);
      flex-shrink: 0;
    }}

    .sidebar-link.active .sidebar-link-bullet {{
      background: var(--primary);
      box-shadow: 0 0 6px var(--primary);
    }}

    /* Main Document Area */
    main.doc-content {{
      flex: 1;
      min-width: 0;
      padding: 40px 52px;
      max-width: var(--content-max-width);
      margin: 0 auto;
    }}

    @media (max-width: 1024px) {{
      aside.sidebar {{
        display: none;
        position: fixed;
        left: 0;
        top: var(--header-height);
        bottom: 0;
        z-index: 850;
        box-shadow: var(--shadow-lg);
      }}
      aside.sidebar.mobile-open {{
        display: flex;
      }}
      main.doc-content {{
        padding: 24px 18px;
      }}
      .search-trigger {{
        min-width: unset;
      }}
    }}

    /* Callout Alert Boxes */
    .callout {{
      margin: 24px 0;
      padding: 16px 20px;
      border-radius: var(--radius-md);
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-left: 4px solid var(--primary);
    }}

    .callout-header {{
      display: flex;
      align-items: center;
      gap: 10px;
      font-weight: 700;
      font-size: 0.95rem;
      margin-bottom: 8px;
      color: var(--primary);
    }}

    .callout-warning {{
      border-left-color: var(--accent-rose);
      background: rgba(244, 63, 94, 0.05);
    }}
    .callout-warning .callout-header {{
      color: var(--accent-rose);
    }}

    .callout-meta {{
      border-left-color: var(--accent-purple);
      background: rgba(192, 132, 252, 0.05);
    }}
    .callout-meta .callout-header {{
      color: var(--accent-purple);
    }}

    .callout-quote {{
      border-left-color: var(--accent-emerald);
      background: rgba(52, 211, 153, 0.05);
      font-style: italic;
    }}
    .callout-quote .callout-header {{
      color: var(--accent-emerald);
      font-style: normal;
    }}

    .callout-body p {{
      margin: 0;
      font-size: 0.94rem;
      color: var(--text-muted);
    }}

    /* Interactive TOC Dashboard Grid */
    .toc-dashboard {{
      margin: 30px 0 60px 0;
      padding: 30px;
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-lg);
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
    }}

    .toc-dashboard-title-row {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      flex-wrap: wrap;
      margin-bottom: 6px;
    }}

    .toc-badge-total {{
      font-size: 0.78rem;
      font-weight: 700;
      text-transform: uppercase;
      padding: 3px 10px;
      border-radius: 999px;
      background: var(--primary-glow);
      color: var(--primary);
      border: 1px solid rgba(56, 189, 248, 0.3);
    }}

    .toc-dashboard-header h2 {{
      font-size: 1.55rem;
      font-weight: 800;
      margin: 0;
    }}

    .toc-dashboard-header p {{
      color: var(--text-muted);
      font-size: 0.95rem;
      margin-bottom: 24px;
      margin-top: 6px;
    }}

    .toc-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 20px;
    }}

    .toc-card {{
      background: var(--bg-base);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      padding: 18px 20px;
      transition: all 0.2s ease;
    }}

    .toc-card:hover {{
      border-color: var(--primary);
      transform: translateY(-2px);
      box-shadow: 0 6px 16px var(--primary-glow);
    }}

    .toc-card-header {{
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 14px;
      padding-bottom: 10px;
      border-bottom: 1px solid var(--border-subtle);
    }}

    .toc-card-icon {{
      color: var(--primary);
      display: flex;
      align-items: center;
    }}

    .toc-card-header h3 {{
      font-size: 1.02rem;
      font-weight: 700;
      color: var(--text-main);
    }}

    .toc-card-list {{
      list-style: none;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }}

    .toc-card-list li a {{
      color: var(--text-muted);
      text-decoration: none;
      font-size: 0.88rem;
      transition: color 0.15s ease;
      display: block;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    .toc-card-list li a:hover {{
      color: var(--primary);
    }}

    /* Guide Chapters */
    .guide-chapter {{
      margin-bottom: 75px;
      padding-bottom: 40px;
      border-bottom: 1px solid var(--border-subtle);
    }}

    .chapter-banner {{
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      padding: 16px 20px;
      margin-bottom: 28px;
    }}

    .banner-top {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      flex-wrap: wrap;
    }}

    [data-category="cat-interview"] .category-pill {{
      background: rgba(236, 72, 153, 0.15) !important;
      color: #f472b6 !important;
      border-color: rgba(236, 72, 153, 0.35) !important;
    }}
    [data-category="cat-fluid2"] .category-pill {{
      background: rgba(168, 85, 247, 0.15) !important;
      color: #c084fc !important;
      border-color: rgba(168, 85, 247, 0.35) !important;
    }}
    .category-pill {{
      font-size: 0.75rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      padding: 3px 10px;
      border-radius: 999px;
      background: var(--primary-glow);
      color: var(--primary);
      border: 1px solid rgba(56, 189, 248, 0.25);
    }}

    .reading-meta {{
      font-size: 0.82rem;
      color: var(--text-dim);
      display: flex;
      align-items: center;
      gap: 6px;
    }}

    .section-jump-chips {{
      display: flex;
      align-items: center;
      gap: 8px;
      margin-top: 14px;
      padding-top: 12px;
      border-top: 1px dashed var(--border-subtle);
      flex-wrap: wrap;
    }}

    .jump-chip {{
      font-size: 0.78rem;
      color: var(--text-muted);
      background: var(--bg-base);
      border: 1px solid var(--border-subtle);
      padding: 3px 10px;
      border-radius: var(--radius-sm);
      text-decoration: none;
      transition: all 0.15s;
    }}

    .jump-chip:hover {{
      color: var(--primary);
      border-color: var(--primary);
    }}

    .jump-chip-more {{
      font-size: 0.75rem;
      color: var(--text-dim);
      font-style: italic;
    }}

    /* Official Graphic Card */
    .official-graphic-card {{
      margin: 28px 0;
      background: var(--bg-surface);
      border: 1px solid var(--border-medium);
      border-radius: var(--radius-md);
      overflow: hidden;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
    }}

    .official-graphic-summary {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 14px 18px;
      background: var(--bg-surface-elevated);
      cursor: pointer;
      user-select: none;
      border-bottom: 1px solid var(--border-subtle);
    }}

    .summary-left {{
      display: flex;
      align-items: center;
      gap: 10px;
      font-weight: 700;
      font-size: 0.95rem;
      color: var(--text-main);
    }}

    .graphic-badge {{
      font-size: 0.72rem;
      padding: 2px 8px;
      border-radius: 999px;
      background: rgba(56, 189, 248, 0.2);
      color: var(--primary);
      font-weight: 600;
    }}

    .svg-diagram-wrapper {{
      padding: 20px;
      background: #ffffff;
      overflow-x: auto;
    }}

    .svg-diagram-content svg {{
      display: block;
      margin: 0 auto;
      max-width: 100%;
      height: auto;
    }}

    .svg-diagram-footer {{
      margin-top: 14px;
      font-size: 0.78rem;
      color: #64748b;
      text-align: right;
    }}

    /* Headings */
    h1, h2, h3, h4, h5, h6 {{
      color: var(--text-main);
      font-weight: 700;
      letter-spacing: -0.015em;
      position: relative;
    }}

    h1 {{
      font-size: 2.35rem;
      font-weight: 800;
      line-height: 1.25;
      margin-bottom: 18px;
    }}

    h2 {{
      font-size: 1.85rem;
      margin: 32px 0 18px 0;
      line-height: 1.3;
    }}

    h3 {{
      font-size: 1.35rem;
      margin: 28px 0 14px 0;
      line-height: 1.35;
      color: #38bdf8;
    }}

    [data-theme="light"] h3 {{
      color: #0284c7;
    }}

    h4 {{
      font-size: 1.1rem;
      margin: 22px 0 10px 0;
    }}

    p {{
      margin-bottom: 16px;
      color: var(--text-main);
    }}

    .heading-anchor {{
      opacity: 0;
      color: var(--primary);
      text-decoration: none;
      margin-left: 8px;
      font-weight: 400;
      transition: opacity 0.2s;
    }}

    h1:hover .heading-anchor,
    h2:hover .heading-anchor,
    h3:hover .heading-anchor,
    h4:hover .heading-anchor {{
      opacity: 1;
    }}

    /* Code Container & ASCII Diagrams */
    .code-container {{
      margin: 24px 0;
      background: var(--bg-code);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      overflow: hidden;
      box-shadow: 0 4px 14px rgba(0, 0, 0, 0.35);
    }}

    .code-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 8px 16px;
      background: rgba(255, 255, 255, 0.03);
      border-bottom: 1px solid var(--border-subtle);
    }}

    .code-badge {{
      font-family: var(--font-mono);
      font-size: 0.72rem;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 4px;
      letter-spacing: 0.04em;
    }}

    .badge-typescript {{ background: rgba(59, 130, 246, 0.2); color: #60a5fa; }}
    .badge-json {{ background: rgba(234, 179, 8, 0.2); color: #facc15; }}
    .badge-bash {{ background: rgba(34, 197, 94, 0.2); color: #4ade80; }}
    .badge-architecture-diagram {{ background: rgba(168, 85, 247, 0.2); color: #c084fc; }}
    .badge-directory-tree {{ background: rgba(20, 184, 166, 0.2); color: #2dd4bf; }}
    .badge-reference, .badge-snippet, .badge-code {{ background: rgba(148, 163, 184, 0.2); color: #cbd5e1; }}

    .copy-btn {{
      display: flex;
      align-items: center;
      gap: 6px;
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid var(--border-subtle);
      color: var(--text-muted);
      padding: 4px 10px;
      border-radius: 4px;
      font-size: 0.76rem;
      cursor: pointer;
      transition: all 0.2s;
    }}

    .copy-btn:hover {{
      background: rgba(255, 255, 255, 0.12);
      color: var(--text-main);
      border-color: var(--border-medium);
    }}

    .copy-btn.copied {{
      background: rgba(34, 197, 94, 0.2);
      color: #4ade80;
      border-color: rgba(34, 197, 94, 0.4);
    }}

    pre {{
      margin: 0;
      padding: 18px 20px;
      overflow-x: auto;
      font-family: var(--font-mono);
      font-size: 0.88rem;
      line-height: 1.45;
      color: #e2e8f0;
    }}

    pre.ascii-diagram {{
      font-size: 0.84rem;
      line-height: 1.28;
      color: #93c5fd;
      background: #090e1a;
      background-image: 
        linear-gradient(rgba(56, 189, 248, 0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(56, 189, 248, 0.03) 1px, transparent 1px);
      background-size: 20px 20px;
      border-left: 3px solid var(--primary);
    }}

    pre.tree-diagram {{
      color: #a7f3d0;
      border-left-color: var(--accent-emerald);
    }}

    /* Pandoc Syntax Highlighting Classes */
    span.kw {{ color: #f43f5e; font-weight: 600; }}
    span.fu {{ color: #38bdf8; }}
    span.dt {{ color: #c084fc; }}
    span.st {{ color: #34d399; }}
    span.co {{ color: #64748b; font-style: italic; }}
    span.dv {{ color: #fbbf24; }}
    span.op {{ color: #94a3b8; }}
    span.at {{ color: #e2e8f0; }}
    span.cf {{ color: #f43f5e; font-weight: 600; }}
    span.bu {{ color: #38bdf8; }}

    /* Inline Code */
    :not(pre) > code {{
      font-family: var(--font-mono);
      font-size: 0.86em;
      background: var(--bg-surface-elevated);
      color: #38bdf8;
      padding: 2px 6px;
      border-radius: 4px;
      border: 1px solid var(--border-subtle);
    }}

    [data-theme="light"] :not(pre) > code {{
      color: #0369a1;
      background: #e2e8f0;
    }}

    /* Responsive Tables */
    .table-responsive {{
      margin: 24px 0;
      overflow-x: auto;
      border-radius: var(--radius-md);
      border: 1px solid var(--border-subtle);
      box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.92rem;
      text-align: left;
    }}

    thead {{
      background: var(--bg-surface-elevated);
      border-bottom: 2px solid var(--border-medium);
    }}

    th {{
      padding: 12px 16px;
      font-weight: 700;
      color: var(--text-main);
      letter-spacing: 0.01em;
    }}

    td {{
      padding: 12px 16px;
      border-bottom: 1px solid var(--border-subtle);
      color: var(--text-main);
      vertical-align: top;
    }}

    tbody tr:nth-child(even) {{
      background: rgba(255, 255, 255, 0.015);
    }}

    [data-theme="light"] tbody tr:nth-child(even) {{
      background: rgba(0, 0, 0, 0.02);
    }}

    tbody tr:hover {{
      background: var(--bg-surface-hover);
    }}

    ul, ol {{
      margin: 16px 0 20px 24px;
      color: var(--text-main);
    }}

    li {{
      margin-bottom: 6px;
    }}

    a {{
      color: var(--primary);
      text-decoration: underline;
      text-underline-offset: 3px;
      transition: color 0.15s;
    }}

    a:hover {{
      color: var(--primary-hover);
    }}

    /* Modal Search Box */
    .search-modal-backdrop {{
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.75);
      backdrop-filter: blur(8px);
      z-index: 1000;
      align-items: flex-start;
      justify-content: center;
      padding-top: 10vh;
    }}

    .search-modal-backdrop.open {{
      display: flex;
    }}

    .search-modal {{
      background: var(--bg-surface);
      border: 1px solid var(--border-medium);
      border-radius: var(--radius-lg);
      width: 90%;
      max-width: 650px;
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6);
      overflow: hidden;
      display: flex;
      flex-direction: column;
      max-height: 75vh;
    }}

    .search-input-box {{
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 16px 20px;
      border-bottom: 1px solid var(--border-subtle);
    }}

    .search-input-box input {{
      flex: 1;
      background: none;
      border: none;
      color: var(--text-main);
      font-size: 1.1rem;
      outline: none;
    }}

    .search-results-list {{
      overflow-y: auto;
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }}

    .search-result-item {{
      padding: 12px 14px;
      border-radius: var(--radius-sm);
      text-decoration: none;
      display: flex;
      flex-direction: column;
      gap: 4px;
      transition: all 0.15s;
    }}

    .search-result-item:hover,
    .search-result-item.selected {{
      background: var(--bg-surface-elevated);
      border-left: 3px solid var(--primary);
    }}

    .result-category {{
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      color: var(--primary);
      letter-spacing: 0.04em;
    }}

    .result-title {{
      font-size: 0.98rem;
      font-weight: 600;
      color: var(--text-main);
    }}

    .result-excerpt {{
      font-size: 0.82rem;
      color: var(--text-dim);
      line-height: 1.4;
    }}

    .search-footer {{
      padding: 10px 18px;
      border-top: 1px solid var(--border-subtle);
      font-size: 0.78rem;
      color: var(--text-dim);
      display: flex;
      align-items: center;
      justify-content: space-between;
      background: var(--bg-base);
    }}

    #back-to-top {{
      position: fixed;
      bottom: 24px;
      right: 24px;
      width: 44px;
      height: 44px;
      border-radius: 50%;
      background: var(--bg-surface-elevated);
      border: 1px solid var(--border-medium);
      color: var(--text-main);
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      opacity: 0;
      pointer-events: none;
      transition: all 0.25s ease;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
      z-index: 700;
    }}

    #back-to-top.visible {{
      opacity: 1;
      pointer-events: auto;
    }}

    #back-to-top:hover {{
      background: var(--primary);
      color: #fff;
      transform: translateY(-2px);
    }}

    @media print {{
      header.site-header, aside.sidebar, #reading-progress, #back-to-top, .search-trigger, .copy-btn {{
        display: none !important;
      }}
      main.doc-content {{
        padding: 0 !important;
        max-width: 100% !important;
      }}
      body {{
        background: #fff !important;
        color: #000 !important;
      }}
      pre.ascii-diagram {{
        background: #f8fafc !important;
        color: #0f172a !important;
        border: 1px solid #cbd5e1 !important;
      }}
    }}
  </style>
</head>
<body>

  <div id="reading-progress"></div>

  <header class="site-header">
    <div class="header-left">
      <button class="btn-icon" id="mobile-menu-toggle" aria-label="Toggle Navigation Menu">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>
      </button>
      <a href="#" class="brand-logo">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="#38bdf8"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
        Fluid Framework
        <span class="brand-badge">Learning Guide</span>
      </a>
    </div>

    <div class="header-actions">
      <button class="search-trigger" id="open-search-btn" aria-label="Search Documentation">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
        <span>Search guide...</span>
        <span class="kbd-shortcut">/</span>
      </button>

      <button class="btn-icon" id="theme-toggle" aria-label="Toggle Dark/Light Mode" title="Toggle Theme">
        <svg id="theme-icon-moon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>
        <svg id="theme-icon-sun" style="display:none;" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>
      </button>
    </div>
  </header>

  <div class="app-layout">
    <aside class="sidebar" id="sidebar">
      <div class="sidebar-filter-wrapper">
        <svg class="sidebar-filter-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
        <input type="text" class="sidebar-filter-input" id="sidebar-filter" placeholder="Filter sections...">
      </div>

      <div class="sidebar-groups">
        {sidebar_categories_html}
      </div>
    </aside>

    <main class="doc-content">
      {assembled_body}
    </main>
  </div>

  <button id="back-to-top" aria-label="Back to Top" title="Back to top">
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="18 15 12 9 6 15"></polyline></svg>
  </button>

  <div class="search-modal-backdrop" id="search-modal">
    <div class="search-modal">
      <div class="search-input-box">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
        <input type="text" id="modal-search-input" placeholder="Search architecture, Kafka, DDS, Routerlicious, GC..." autocomplete="off">
        <span class="kbd-shortcut">ESC</span>
      </div>
      <div class="search-results-list" id="modal-search-results">
      </div>
      <div class="search-footer">
        <span>Navigate with <b>&uarr; &darr;</b> and <b>ENTER</b></span>
        <span><b>ESC</b> to close</span>
      </div>
    </div>
  </div>

  <script>
    const searchData = {json.dumps(search_index)};

    window.addEventListener('scroll', () => {{
      const winScroll = document.body.scrollTop || document.documentElement.scrollTop;
      const height = document.documentElement.scrollHeight - document.documentElement.clientHeight;
      const scrolled = (winScroll / height) * 100;
      document.getElementById('reading-progress').style.width = scrolled + '%';

      const btt = document.getElementById('back-to-top');
      if (winScroll > 400) {{
        btt.classList.add('visible');
      }} else {{
        btt.classList.remove('visible');
      }}
    }});

    document.getElementById('back-to-top').addEventListener('click', () => {{
      window.scrollTo({{ top: 0, behavior: 'smooth' }});
    }});

    const themeToggleBtn = document.getElementById('theme-toggle');
    const moonIcon = document.getElementById('theme-icon-moon');
    const sunIcon = document.getElementById('theme-icon-sun');

    function setTheme(theme) {{
      document.documentElement.setAttribute('data-theme', theme);
      localStorage.setItem('ff_theme', theme);
      if (theme === 'light') {{
        moonIcon.style.display = 'none';
        sunIcon.style.display = 'block';
      }} else {{
        moonIcon.style.display = 'block';
        sunIcon.style.display = 'none';
      }}
    }}

    const savedTheme = localStorage.getItem('ff_theme') || 'dark';
    setTheme(savedTheme);

    themeToggleBtn.addEventListener('click', () => {{
      const current = document.documentElement.getAttribute('data-theme');
      setTheme(current === 'dark' ? 'light' : 'dark');
    }});

    const mobileToggle = document.getElementById('mobile-menu-toggle');
    const sidebar = document.getElementById('sidebar');
    mobileToggle.addEventListener('click', () => {{
      sidebar.classList.toggle('mobile-open');
    }});

    document.querySelectorAll('.sidebar-link').forEach(link => {{
      link.addEventListener('click', () => {{
        sidebar.classList.remove('mobile-open');
      }});
    }});

    function toggleSidebarGroup(btn) {{
      const group = btn.closest('.sidebar-group');
      group.classList.toggle('collapsed');
    }}

    const sidebarFilter = document.getElementById('sidebar-filter');
    sidebarFilter.addEventListener('input', (e) => {{
      const q = e.target.value.toLowerCase().trim();
      document.querySelectorAll('.sidebar-item').forEach(item => {{
        const text = item.textContent.toLowerCase();
        if (!q || text.includes(q)) {{
          item.style.display = '';
        }} else {{
          item.style.display = 'none';
        }}
      }});
    }});

    const observerOptions = {{
      root: null,
      rootMargin: '-80px 0px -70% 0px',
      threshold: 0
    }};

    const sections = document.querySelectorAll('.guide-chapter');
    const sidebarLinks = document.querySelectorAll('.sidebar-link');

    const observer = new IntersectionObserver((entries) => {{
      entries.forEach(entry => {{
        if (entry.isIntersecting) {{
          const id = entry.target.id;
          sidebarLinks.forEach(link => {{
            if (link.getAttribute('href') === '#' + id) {{
              link.classList.add('active');
              link.scrollIntoView({{ block: 'nearest', behavior: 'smooth' }});
            }} else {{
              link.classList.remove('active');
            }}
          }});
        }}
      }});
    }}, observerOptions);

    sections.forEach(s => observer.observe(s));

    function copySnippet(btn) {{
      const container = btn.closest('.code-container');
      const pre = container.querySelector('pre');
      const text = pre.innerText;

      navigator.clipboard.writeText(text).then(() => {{
        btn.classList.add('copied');
        const label = btn.querySelector('.copy-label');
        if (label) label.textContent = 'Copied! ✓';
        setTimeout(() => {{
          btn.classList.remove('copied');
          if (label) label.textContent = 'Copy';
        }}, 2000);
      }}).catch(err => {{
        console.error('Failed to copy', err);
      }});
    }}

    const searchModal = document.getElementById('search-modal');
    const openSearchBtn = document.getElementById('open-search-btn');
    const searchInput = document.getElementById('modal-search-input');
    const searchResults = document.getElementById('modal-search-results');
    let selectedIndex = 0;

    function openSearch() {{
      searchModal.classList.add('open');
      searchInput.value = '';
      renderSearchResults('');
      searchInput.focus();
    }}

    function closeSearch() {{
      searchModal.classList.remove('open');
    }}

    openSearchBtn.addEventListener('click', openSearch);

    searchModal.addEventListener('click', (e) => {{
      if (e.target === searchModal) closeSearch();
    }});

    window.addEventListener('keydown', (e) => {{
      if (e.key === '/' && document.activeElement !== searchInput && !['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) {{
        e.preventDefault();
        openSearch();
      }} else if ((e.key === 'k' || e.key === 'K') && (e.metaKey || e.ctrlKey)) {{
        e.preventDefault();
        openSearch();
      }} else if (e.key === 'Escape' && searchModal.classList.contains('open')) {{
        closeSearch();
      }}
    }});

    function renderSearchResults(query) {{
      const q = query.toLowerCase().trim();
      searchResults.innerHTML = '';
      if (!q) {{
        searchResults.innerHTML = '<div style="padding: 24px; text-align: center; color: var(--text-dim);">Type keywords like "Kafka", "Deli", "DDS", "ToB", "Summary", or "Lumberjack"...</div>';
        return;
      }}

      const matches = searchData.filter(item => 
        item.title.toLowerCase().includes(q) || 
        item.excerpt.toLowerCase().includes(q) ||
        item.category.toLowerCase().includes(q)
      ).slice(0, 15);

      if (matches.length === 0) {{
        searchResults.innerHTML = '<div style="padding: 24px; text-align: center; color: var(--text-dim);">No results found for "' + query + '"</div>';
        return;
      }}

      matches.forEach((item, idx) => {{
        const a = document.createElement('a');
        a.href = '#' + item.id;
        a.className = 'search-result-item' + (idx === 0 ? ' selected' : '');
        a.innerHTML = `
          <div class="result-category">${{item.category}}</div>
          <div class="result-title">${{highlightMatch(item.title, q)}}</div>
          ${{item.excerpt ? `<div class="result-excerpt">${{highlightMatch(item.excerpt, q)}}</div>` : ''}}
        `;
        a.addEventListener('click', () => {{
          closeSearch();
        }});
        searchResults.appendChild(a);
      }});

      selectedIndex = 0;
    }}

    function highlightMatch(text, query) {{
      const regex = new RegExp(`(${{query.replace(/[-\\/\\\\^$*+?.()|[\\]{{}}]/g, '\\\\$&')}})`, 'gi');
      return text.replace(regex, '<mark style="background: rgba(56, 189, 248, 0.3); color: inherit; padding: 1px 3px; border-radius: 2px;">$1</mark>');
    }}

    searchInput.addEventListener('input', (e) => {{
      renderSearchResults(e.target.value);
    }});

    searchInput.addEventListener('keydown', (e) => {{
      const items = searchResults.querySelectorAll('.search-result-item');
      if (items.length === 0) return;

      if (e.key === 'ArrowDown') {{
        e.preventDefault();
        items[selectedIndex]?.classList.remove('selected');
        selectedIndex = (selectedIndex + 1) % items.length;
        items[selectedIndex]?.classList.add('selected');
        items[selectedIndex]?.scrollIntoView({{ block: 'nearest' }});
      }} else if (e.key === 'ArrowUp') {{
        e.preventDefault();
        items[selectedIndex]?.classList.remove('selected');
        selectedIndex = (selectedIndex - 1 + items.length) % items.length;
        items[selectedIndex]?.classList.add('selected');
        items[selectedIndex]?.scrollIntoView({{ block: 'nearest' }});
      }} else if (e.key === 'Enter') {{
        e.preventDefault();
        items[selectedIndex]?.click();
      }}
    }});
  </script>
</body>
</html>
'''

with open(OUT_PATH, "w", encoding="utf-8") as f:
    f.write(MASTER_HTML)

GUIDE_DIR = "/Users/dhiraj.thakur/project/fluid-framework-learning-guide"
for target_name in ["index.html", "learning.html"]:
    target_path = os.path.join(GUIDE_DIR, target_name)
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(MASTER_HTML)
    print(f"Synced to guide: {target_path}")

print(f"Successfully generated: {OUT_PATH}")
print(f"Final file size: {os.path.getsize(OUT_PATH)} bytes")