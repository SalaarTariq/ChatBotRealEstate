(() => {
  const form = document.getElementById("search-form");
  const queryInput = document.getElementById("query");
  const searchBtn = document.getElementById("search-btn");
  const statusPanel = document.getElementById("status");
  const errorPanel = document.getElementById("error");
  const resultsSection = document.getElementById("results");
  const researchSection = document.getElementById("research");
  const listingGrid = document.getElementById("listing-grid");
  const sourceLink = document.getElementById("source-link");
  const noListings = document.getElementById("no-listings");
  const researchBody = document.getElementById("research-body");

  const stepFetch = document.querySelector('.status-step[data-step="fetch"]');
  const stepResearch = document.querySelector('.status-step[data-step="research"]');

  document.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      queryInput.value = chip.dataset.q;
      queryInput.focus();
    });
  });

  const escapeHtml = (s) =>
    String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");

  const renderListings = (listings, sourceUrl) => {
    listingGrid.innerHTML = "";
    if (!listings || !listings.length) {
      noListings.classList.remove("hidden");
      return;
    }
    noListings.classList.add("hidden");

    for (const l of listings) {
      const card = document.createElement("article");
      card.className = "listing-card";
      card.innerHTML = `
        <span class="rank-badge">#${escapeHtml(l.rank)} pick</span>
        <h3 class="listing-title">${escapeHtml(l.title || "Untitled listing")}</h3>
        <div class="listing-price">${escapeHtml(l.price || "Price on request")}</div>
        <div class="listing-location">${escapeHtml(l.location || "Location not specified")}</div>
        <div class="listing-meta">
          ${l.beds ? `<div>🛏 <strong>${escapeHtml(l.beds)}</strong> Beds</div>` : ""}
          ${l.baths ? `<div>🛁 <strong>${escapeHtml(l.baths)}</strong> Baths</div>` : ""}
          ${l.area ? `<div>📐 <strong>${escapeHtml(l.area)}</strong></div>` : ""}
        </div>
        ${l.url ? `<a class="listing-cta" href="${escapeHtml(l.url)}" target="_blank" rel="noopener">View on Zameen ↗</a>` : ""}
      `;
      listingGrid.appendChild(card);
    }

    if (sourceUrl) {
      sourceLink.href = sourceUrl;
      sourceLink.classList.remove("hidden");
    } else {
      sourceLink.classList.add("hidden");
    }
  };

  if (window.marked && typeof window.marked.setOptions === "function") {
    window.marked.setOptions({ mangle: false, headerIds: false });
  }

  const sanitizeRenderedMarkdown = (html) =>
    html
      .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, "")
      .replace(/\son\w+\s*=\s*"[^"]*"/gi, "")
      .replace(/\son\w+\s*=\s*'[^']*'/gi, "");

  const renderResearch = (md) => {
    if (!md || !md.trim()) {
      researchSection.classList.add("hidden");
      return;
    }
    const html = window.marked
      ? sanitizeRenderedMarkdown(window.marked.parse(md))
      : `<pre>${escapeHtml(md)}</pre>`;
    researchBody.innerHTML = html;
    researchSection.classList.remove("hidden");
  };

  const markStep = (step, state) => {
    step.classList.remove("active", "done");
    if (state) step.classList.add(state);
  };

  const startLoading = () => {
    searchBtn.classList.add("loading");
    searchBtn.disabled = true;
    statusPanel.classList.remove("hidden");
    markStep(stepFetch, "active");
    markStep(stepResearch, null);
    errorPanel.classList.add("hidden");
    resultsSection.classList.add("hidden");
    researchSection.classList.add("hidden");
  };

  const stopLoading = () => {
    searchBtn.classList.remove("loading");
    searchBtn.disabled = false;
    markStep(stepFetch, "done");
    markStep(stepResearch, "done");
    setTimeout(() => statusPanel.classList.add("hidden"), 1200);
  };

  const showError = (msg) => {
    errorPanel.textContent = msg;
    errorPanel.classList.remove("hidden");
    statusPanel.classList.add("hidden");
    searchBtn.classList.remove("loading");
    searchBtn.disabled = false;
  };

  const renderResult = (data) => {
    renderListings(data.listings || [], data.source_url || "");
    renderResearch(data.research_markdown || "");

    // Cached badge in the section head.
    const head = resultsSection.querySelector(".section-head");
    let badge = head ? head.querySelector(".cached-badge") : null;
    if (data.cached) {
      if (!badge && head) {
        badge = document.createElement("span");
        badge.className = "cached-badge";
        badge.textContent = "Cached";
        head.appendChild(badge);
      }
    } else if (badge) {
      badge.remove();
    }

    resultsSection.classList.remove("hidden");
    resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  let currentSource = null;

  const runStreamingSearch = (topic) => {
    if (currentSource) {
      currentSource.close();
      currentSource = null;
    }
    startLoading();

    const url = "/search/stream?topic=" + encodeURIComponent(topic);
    const es = new EventSource(url);
    currentSource = es;

    let receivedResult = false;

    const close = () => {
      if (currentSource === es) currentSource = null;
      es.close();
    };

    es.addEventListener("task_done", (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.task === "fetch") {
          markStep(stepFetch, "done");
          markStep(stepResearch, "active");
        } else if (data.task === "research") {
          markStep(stepResearch, "done");
        }
      } catch (_) {}
    });

    es.addEventListener("result", (e) => {
      try {
        const data = JSON.parse(e.data);
        receivedResult = true;
        renderResult(data);
      } catch (err) {
        showError("Failed to parse result: " + err.message);
      }
    });

    es.addEventListener("done", () => {
      stopLoading();
      close();
    });

    es.addEventListener("error", (e) => {
      // SSE 'error' fires both on server-sent error events (with data) and
      // transport-level disconnects (no data, no readyState close).
      if (e.data) {
        try {
          const data = JSON.parse(e.data);
          showError(data.error || "Something went wrong.");
        } catch (_) {
          showError("Server error.");
        }
        close();
        return;
      }
      if (es.readyState === EventSource.CLOSED) {
        if (!receivedResult) showError("Connection closed before results arrived.");
        close();
      }
    });
  };

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const topic = queryInput.value.trim();
    if (!topic) {
      queryInput.focus();
      return;
    }
    runStreamingSearch(topic);
  });
})();
