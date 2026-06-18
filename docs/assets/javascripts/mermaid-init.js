// Render Mermaid diagrams (including C4) in the MkDocs site.
// pymdownx.superfences emits ```mermaid blocks as <pre class="mermaid"><code>...</code></pre>.
// Mermaid's run() expects the definition as the element's text content, so unwrap
// the inner <code> before initializing.
(function () {
  function init() {
    if (typeof mermaid === "undefined") {
      return;
    }
    document.querySelectorAll("pre.mermaid > code").forEach(function (code) {
      var pre = code.parentNode;
      pre.textContent = code.textContent;
    });
    mermaid.initialize({ startOnLoad: true });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
