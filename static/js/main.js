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

  const renderResearch = (md) => {
    if (!md || !md.trim()) {
      researchSection.classList.add("hidden");
      return;
    }
    researchBody.innerHTML = window.marked ? window.marked.parse(md) : `<pre>${escapeHtml(md)}</pre>`;
    researchSection.classList.remove("hidden");
  };

  const setLoading = (loading) => {
    if (loading) {
      searchBtn.classList.add("loading");
      searchBtn.disabled = true;
      statusPanel.classList.remove("hidden");
      stepFetch.classList.add("active");
      stepFetch.classList.remove("done");
      stepResearch.classList.remove("active", "done");
      errorPanel.classList.add("hidden");
      resultsSection.classList.add("hidden");
      researchSection.classList.add("hidden");

      // After ~12s assume fetch is done and research is running.
      window.__statusTimer = setTimeout(() => {
        stepFetch.classList.remove("active");
        stepFetch.classList.add("done");
        stepResearch.classList.add("active");
      }, 12000);
    } else {
      searchBtn.classList.remove("loading");
      searchBtn.disabled = false;
      clearTimeout(window.__statusTimer);
      stepFetch.classList.add("done");
      stepFetch.classList.remove("active");
      stepResearch.classList.add("done");
      stepResearch.classList.remove("active");
      setTimeout(() => statusPanel.classList.add("hidden"), 1200);
    }
  };

  const showError = (msg) => {
    errorPanel.textContent = msg;
    errorPanel.classList.remove("hidden");
  };

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const topic = queryInput.value.trim();
    if (!topic) {
      queryInput.focus();
      return;
    }

    setLoading(true);
    try {
      const resp = await fetch("/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic }),
      });
      const data = await resp.json();
      if (!resp.ok) {
        showError(data.error || "Something went wrong while running the agents.");
        return;
      }
      renderListings(data.listings || [], data.source_url || "");
      renderResearch(data.research_markdown || "");
      resultsSection.classList.remove("hidden");
      resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (err) {
      showError("Network error: " + err.message);
    } finally {
      setLoading(false);
    }
  });
})();
