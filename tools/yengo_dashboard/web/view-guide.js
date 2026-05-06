// view-guide.js — Guide tab (markdown docs viewer)
//
// Renders docs/ via marked.js (loaded from CDN in index.html).
// Backend serves the file tree at /api/docs/tree and individual files at
// /api/docs/file?path=...  (read-only, scoped to docs/).

import { $, $$, getJSON, escapeHtml, errorBlock } from "./ui.js";

let _guideTree = null;     // cached tree from /api/docs/tree
let _guideCurrent = null;  // currently-loaded doc path

export async function renderGuide() {
  const root = $("#view-guide");
  if (!root.dataset.bootstrapped) {
    root.innerHTML = `
      <div class="guide-layout">
        <aside id="guide-tree" class="guide-tree">
          <div class="text-zinc-500 text-xs">Loading docs…</div>
        </aside>
        <article id="guide-content" class="guide-content">
          <h1>Yen-Go Dashboard — Guide</h1>
          <p>Select a document from the tree to read it.</p>
          <p class="text-zinc-500 text-sm">
            Docs are served read-only from the project's <code>docs/</code> directory.
            Click any link on the left to load it.
          </p>
        </article>
      </div>
    `;
    root.dataset.bootstrapped = "1";
  }
  if (_guideTree === null) {
    try {
      _guideTree = await getJSON("/api/docs/tree");
      paintGuideTree();
    } catch (err) {
      $("#guide-tree").innerHTML = errorBlock("GET /api/docs/tree", err);
    }
  }
}

function paintGuideTree() {
  const tree = _guideTree;
  if (!tree) return;
  const html = renderGuideNode(tree, 0);
  $("#guide-tree").innerHTML = html || `<div class="text-zinc-500 text-xs">No docs found.</div>`;
  $("#guide-tree").addEventListener("click", onGuideClick);
}

function renderGuideNode(node, depth) {
  if (node.type === "file") {
    const label = node.name.replace(/\.md$/i, "").replace(/[-_]/g, " ");
    return `<a href="#guide:${encodeURIComponent(node.path)}"
              data-path="${escapeHtml(node.path)}"
              class="${_guideCurrent === node.path ? "active" : ""}">${escapeHtml(label)}</a>`;
  }
  // dir
  const children = (node.children || []).map((c) => renderGuideNode(c, depth + 1)).join("");
  if (!children) return "";
  if (depth === 0) {
    return children; // skip root wrapper
  }
  return `<details ${depth <= 1 ? "open" : ""}>
    <summary>${escapeHtml(node.name)}</summary>
    <div style="padding-left:${depth * 0.5}rem">${children}</div>
  </details>`;
}

function onGuideClick(e) {
  const a = e.target.closest("a[data-path]");
  if (!a) return;
  e.preventDefault();
  loadGuideDoc(a.dataset.path);
}

export async function loadGuideDoc(path) {
  _guideCurrent = path;
  $$("#guide-tree a").forEach((a) => a.classList.toggle("active", a.dataset.path === path));
  history.replaceState(null, "", `/guide/${path.split("/").map(encodeURIComponent).join("/")}`);
  const article = $("#guide-content");
  article.innerHTML = `<div class="text-zinc-500 text-sm">Loading <code>${escapeHtml(path)}</code>…</div>`;
  try {
    const r = await fetch(`/api/docs/file?path=${encodeURIComponent(path)}`);
    if (!r.ok) {
      const body = await r.text();
      article.innerHTML = errorBlock(`GET /api/docs/file?path=${path}`, { status: r.status, body });
      return;
    }
    const md = await r.text();
    if (window.marked) {
      window.marked.setOptions({ gfm: true, breaks: false });
      article.innerHTML = window.marked.parse(md);
    } else {
      article.innerHTML = `<pre>${escapeHtml(md)}</pre>`;
    }
    if (window.lucide?.createIcons) window.lucide.createIcons();
    article.scrollTop = 0;
  } catch (err) {
    article.innerHTML = errorBlock("loadGuideDoc", { body: String(err) });
  }
}
