"use strict";

const main = document.getElementById("main");
const MAX_CHARS = 2000;
const MAX_WORDS = 500;
let renderToken = 0;

/* ---------- helpers ---------- */

function el(tag, props, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props || {})) {
    if (value === null || value === undefined || value === false) continue;
    if (key === "class") node.className = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value === true ? "" : value);
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child.nodeType ? child : document.createTextNode(String(child)));
  }
  return node;
}

async function api(method, path, body) {
  const options = { method, headers: {} };
  if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  let response;
  try {
    response = await fetch(path, options);
  } catch (networkError) {
    const err = new Error("Could not reach the local server. Is it still running?");
    err.status = 0;
    throw err;
  }
  let payload = null;
  try {
    payload = await response.json();
  } catch (parseError) {
    payload = null;
  }
  if (!response.ok) {
    const err = new Error((payload && payload.error) || `Request failed (${response.status}).`);
    err.status = response.status;
    err.payload = payload || {};
    throw err;
  }
  return payload;
}

function setSafeText(node, text) {
  if (typeof node.setHTML === "function") {
    try {
      node.setHTML(text);
      return node;
    } catch (sanitizeError) {
      /* fall through to plain text */
    }
  }
  node.textContent = text;
  return node;
}

function clamp(text) {
  const overChars = text.length > MAX_CHARS;
  if (!overChars && text.split(/\s+/).filter(Boolean).length <= MAX_WORDS) return { text, truncated: false };
  let cut = text.slice(0, MAX_CHARS);
  if (overChars && !/\s/.test(text[MAX_CHARS])) {
    const boundary = Math.max(cut.lastIndexOf(" "), cut.lastIndexOf("\n"), cut.lastIndexOf("\t"));
    if (boundary > 0) cut = cut.slice(0, boundary);
  }
  const words = [...cut.matchAll(/\S+/g)];
  if (words.length > MAX_WORDS) {
    const last = words[MAX_WORDS - 1];
    cut = cut.slice(0, last.index + last[0].length);
  }
  return { text: cut.trimEnd(), truncated: true };
}

function formatTime(iso) {
  if (!iso) return "unknown time";
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : date.toLocaleString();
}

function formatStamp(iso) {
  if (!iso) return "unknown time";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const two = (n) => String(n).padStart(2, "0");
  return `${two(d.getDate())}/${two(d.getMonth() + 1)}/${d.getFullYear()} ${two(d.getHours())}:${two(d.getMinutes())}:${two(d.getSeconds())}`;
}

function formatDuration(totalSeconds) {
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  if (h) return `${h}h ${m}m ${s}s`;
  if (m) return `${m}m ${s}s`;
  return `${s}s`;
}

function pluralize(count, noun) {
  return `${count} ${noun}${count === 1 ? "" : "s"}`;
}

function show(...nodes) {
  main.replaceChildren(...nodes.flat().filter(Boolean));
}

function errorNotice(err) {
  return el("div", { class: "notice error", role: "alert" }, el("p", {}, err.message));
}

function pageHref(basePath, params) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params || {})) {
    if (value === null || value === undefined) continue;
    const normalized = key === "q" ? String(value).trim() : String(value);
    if (normalized === "") continue;
    query.set(key, normalized);
  }
  const suffix = query.toString();
  return suffix ? `${basePath}?${suffix}` : basePath;
}

function pager(basePath, page, hasMore, params = {}) {
  if (page <= 1 && !hasMore) return null;
  return el(
    "nav",
    { class: "pager", "aria-label": "Pagination" },
    page > 1 ? el("a", { href: pageHref(basePath, { ...params, page: page - 1 }) }, "Previous page") : null,
    el("span", { class: "muted" }, `Page ${page}`),
    hasMore ? el("a", { href: pageHref(basePath, { ...params, page: page + 1 }) }, "Next page") : null
  );
}

/* ---------- invalid ratings recovery (FR-016) ---------- */

function invalidRatingsNotice(onReset) {
  const button = el("button", { type: "button", class: "danger" }, "Delete ratings and start over");
  const status = el("p", { role: "status" });
  button.addEventListener("click", async () => {
    button.disabled = true;
    try {
      await api("POST", "/api/ratings/reset");
      onReset();
    } catch (err) {
      button.disabled = false;
      status.textContent = err.message;
    }
  });
  return el(
    "div",
    { class: "notice warn", role: "alert" },
    el("p", {}, el("strong", {}, "Your saved ratings can't be read.")),
    el("p", {}, "The local ratings file is damaged, so ratings are hidden and can't be saved. Deleting it removes all saved ratings and lets you start fresh."),
    el("p", {}, button),
    status
  );
}

function invalidFavoritesNotice(onReset) {
  const button = el("button", { type: "button", class: "danger" }, "Delete favorites and start over");
  const status = el("p", { role: "status" });
  button.addEventListener("click", async () => {
    button.disabled = true;
    try {
      await api("POST", "/api/favorites/reset");
      onReset();
    } catch (err) {
      button.disabled = false;
      status.textContent = err.message;
    }
  });
  return el(
    "div",
    { class: "notice warn", role: "alert" },
    el("p", {}, el("strong", {}, "Your saved favorite prompts can't be read.")),
    el("p", {}, "The local favorites file is damaged, so favorite prompts are hidden and can't be saved. Deleting it removes all saved favorites and lets you start fresh."),
    el("p", {}, button),
    status
  );
}

/* ---------- rating control (FR-005, FR-006, FR-009) ---------- */

function ratingControl({ promptId, sessionId, position, value, onSaved, onInvalid }) {
  const status = el("span", { class: "muted", role: "status" });
  const wrapper = el("div", { class: "rating", role: "group", "aria-label": "Rate this prompt from 1 to 10" }, el("span", {}, "Rating"));
  const buttons = [];

  function paint(current) {
    buttons.forEach((b, i) => b.setAttribute("aria-pressed", String(i + 1 === current)));
  }

  for (let n = 1; n <= 10; n++) {
    const button = el("button", { type: "button", "aria-pressed": "false", title: `Rate ${n} out of 10` }, String(n));
    button.addEventListener("click", async () => {
      buttons.forEach((b) => (b.disabled = true));
      status.textContent = "Saving…";
      try {
        const record = await api("PUT", `/api/ratings/${encodeURIComponent(promptId)}`, {
          value: n,
          session_id: sessionId,
          position,
        });
        paint(record.value);
        status.textContent = "Saved";
        if (onSaved) onSaved(record);
      } catch (err) {
        status.textContent = err.message;
        if (err.payload && err.payload.ratings_invalid && onInvalid) onInvalid();
      } finally {
        buttons.forEach((b) => (b.disabled = false));
      }
    });
    buttons.push(button);
    wrapper.append(button);
  }
  wrapper.append(status);
  paint(value);
  return wrapper;
}

/* ---------- text with "show more" (FR-013) ---------- */

function expandableText(initialText, isTruncated, loadFull) {
  const body = el("div", { class: "text" });
  setSafeText(body, initialText + (isTruncated ? "…" : ""));
  const holder = el("div", {}, body);
  if (isTruncated) {
    const more = el("button", { type: "button", class: "link" }, "Show more");
    more.addEventListener("click", async () => {
      more.disabled = true;
      try {
        setSafeText(body, await loadFull());
        more.remove();
      } catch (err) {
        more.disabled = false;
        more.textContent = `Show more (${err.message})`;
      }
    });
    holder.append(more);
  }
  return holder;
}

function clampedText(fullText) {
  const { text, truncated } = clamp(fullText);
  return expandableText(text, truncated, async () => fullText);
}

/* ---------- session list (FR-001) ---------- */

function searchForm(query = "") {
  const label = el("label", { for: "prompt-search" }, "Search prompts");
  const input = el("input", {
    id: "prompt-search",
    type: "search",
    name: "q",
    value: query,
    placeholder: "Search prompts from the last 7 days",
    "aria-label": "Search prompts from the last 7 days",
  });
  const form = el(
    "form",
    { class: "search-form" },
    input,
    el("button", { type: "submit" }, "Search"),
    query ? el("a", { href: "#/sessions", class: "muted" }, "Clear") : null
  );
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const next = input.value.trim();
    location.hash = next ? pageHref("#/sessions", { q: next }) : "#/sessions";
  });
  return el(
    "div",
    { class: "search-box" },
    label,
    form,
    el("p", { class: "muted" }, "Searches prompt text across all sessions from the last 7 days.")
  );
}

async function renderSessionList(page, token) {
  show(el("h2", {}, "Sessions"), searchForm(), el("p", { class: "muted" }, "Loading…"));
  let data;
  try {
    data = await api("GET", `/api/sessions?page=${page}`);
  } catch (err) {
    if (token === renderToken) show(el("h2", {}, "Sessions"), searchForm(), errorNotice(err));
    return;
  }
  if (token !== renderToken) return;

  if (data.sessions.length === 0) {
    show(
      el("h2", {}, "Sessions"),
      el(
        "div",
        { class: "notice" },
        el("p", {}, page > 1 ? "There are no more sessions." : "No Claude Code conversations found yet."),
        page > 1
          ? el("p", {}, el("a", { href: "#/sessions" }, "Back to the first page"))
          : el("p", { class: "muted" }, "Sessions appear here once you've used Claude Code in a project on this machine.")
      )
    );
    return;
  }

  const items = data.sessions.map((s) => {
    const title = el("strong", {});
    const fallbackTitle = s.is_parseable ? "(no prompt text)" : "(unreadable session)";
    setSafeText(title, s.title || fallbackTitle);
    return el(
      "li",
      {},
      el(
        "a",
        { class: "row", href: `#/sessions/${encodeURIComponent(s.session_id)}` },
        title,
        el(
          "span",
          { class: "meta" },
          el("span", {}, formatTime(s.last_activity_at)),
          s.project_path ? el("span", {}, s.project_path) : null,
          el("span", {}, pluralize(s.prompt_count, "prompt")),
          s.is_parseable ? null : el("span", { class: "badge" }, "Couldn't be read")
        )
      )
    );
  });
  show(el("h2", {}, "Sessions"), searchForm(), el("ul", { class: "items" }, items), pager("#/sessions", data.page, data.has_more));
}

function searchResultCard(prompt) {
  const sessionTitle = prompt.session_title || "(untitled session)";
  return el(
    "article",
    {},
    el(
      "p",
      { class: "meta" },
      el("span", {}, "Session: "),
      el("a", { href: `#/sessions/${encodeURIComponent(prompt.session_id)}` }, sessionTitle),
      el("span", {}, formatStamp(prompt.timestamp)),
      prompt.project_path ? el("span", {}, prompt.project_path) : null
    ),
    expandableText(prompt.text, prompt.is_truncated, async () => {
      const full = await api(
        "GET",
        `/api/sessions/${encodeURIComponent(prompt.session_id)}/prompts/${encodeURIComponent(prompt.prompt_id)}`
      );
      return full.text;
    })
  );
}

async function renderPromptSearch(query, page, token) {
  show(el("h2", {}, "Search results"), searchForm(query), el("p", { class: "muted" }, "Loading…"));
  let data;
  try {
    data = await api("GET", `/api/prompts/search?q=${encodeURIComponent(query)}&page=${page}`);
  } catch (err) {
    if (token === renderToken) show(el("h2", {}, "Search results"), searchForm(query), errorNotice(err));
    return;
  }
  if (token !== renderToken) return;

  if (data.prompts.length === 0) {
    show(
      el("h2", {}, "Search results"),
      searchForm(query),
      el("div", { class: "notice" }, el("p", {}, `No prompts from the last 7 days matched “${query}”.`))
    );
    return;
  }

  show(
    el("h2", {}, "Search results"),
    searchForm(query),
    el("p", { class: "muted" }, `Showing matches for “${data.query}”.`),
    ...data.prompts.map((prompt) => searchResultCard(prompt)),
    pager("#/sessions", data.page, data.has_more, { q: data.query })
  );
}

/* ---------- session detail (FR-003, FR-004) ---------- */

function promptCard(sessionId, prompt, onInvalid) {
  const detailBox = el("div");
  let loaded = false;

  const summaryParts = ["Claude's response"];
  if (prompt.duration_seconds !== null && prompt.duration_seconds !== undefined) {
    summaryParts.push(`Claude worked for ${formatDuration(prompt.duration_seconds)}`);
  }
  if (prompt.activity_summary) summaryParts.push(`Claude ${prompt.activity_summary}`);
  const details = el("details", {}, el("summary", {}, summaryParts.join(" - ")), detailBox);
  details.addEventListener("toggle", async () => {
    if (!details.open || loaded) return;
    loaded = true;
    detailBox.replaceChildren(el("p", { class: "muted" }, "Loading…"));
    try {
      const full = await api(
        "GET",
        `/api/sessions/${encodeURIComponent(sessionId)}/prompts/${encodeURIComponent(prompt.prompt_id)}`
      );
      detailBox.replaceChildren(
        full.response_text
          ? el("div", { class: "response" }, clampedText(full.response_text))
          : el("p", { class: "muted" }, "No text response was recorded for this prompt.")
      );
    } catch (err) {
      loaded = false;
      detailBox.replaceChildren(errorNotice(err));
    }
  });

  const text = expandableText(prompt.text, prompt.is_truncated, async () => {
    const full = await api(
      "GET",
      `/api/sessions/${encodeURIComponent(sessionId)}/prompts/${encodeURIComponent(prompt.prompt_id)}`
    );
    return full.text;
  });

  return el(
    "article",
    {},
    el("p", { class: "meta" }, `Prompt ${prompt.position + 1}: ${formatStamp(prompt.timestamp)}`),
    text,
    details,
    ratingControl({
      promptId: prompt.prompt_id,
      sessionId,
      position: prompt.position,
      value: prompt.rating,
      onInvalid,
    })
  );
}

function isEmptyPrompt(prompt) {
  if (prompt.has_response) return false;
  const probe = document.createElement("div");
  setSafeText(probe, prompt.text);
  return probe.textContent.trim() === "";
}

function promptStack(sessionId, prompts, onInvalid) {
  if (prompts.length === 0) return el("div", { class: "notice" }, el("p", {}, "This session has no prompts to show."));
  const items = [];
  for (let i = 0; i < prompts.length; ) {
    if (!isEmptyPrompt(prompts[i])) {
      items.push(promptCard(sessionId, prompts[i], onInvalid));
      i += 1;
      continue;
    }
    let j = i;
    while (j < prompts.length && isEmptyPrompt(prompts[j])) j += 1;
    const run = prompts.slice(i, j);
    items.push(
      el(
        "details",
        { class: "empty-group" },
        el("summary", {}, `Empty prompts and responses (${run.length})`),
        el("div", { class: "stack" }, run.map((p) => promptCard(sessionId, p, onInvalid)))
      )
    );
    i = j;
  }
  return el("div", { class: "stack" }, items);
}

async function renderSessionDetail(sessionId, token) {
  const back = el("a", { class: "back", href: "#/sessions" }, "Back to sessions");
  show(back, el("p", { class: "muted" }, "Loading…"));
  let data;
  try {
    data = await api("GET", `/api/sessions/${encodeURIComponent(sessionId)}`);
  } catch (err) {
    if (token === renderToken) show(back, errorNotice(err));
    return;
  }
  if (token !== renderToken) return;

  const rerender = () => renderSessionDetail(sessionId, ++renderToken);
  const heading = el(
    "div",
    {},
    el("h2", {}, data.project_path || "Session"),
    el("p", { class: "meta" }, el("span", {}, `Last active ${formatTime(data.last_activity_at)}`), el("span", {}, pluralize(data.prompts.length, "prompt")))
  );

  if (!data.is_parseable) {
    show(back, heading, el("div", { class: "notice warn", role: "alert" }, el("p", {}, data.error || "This session couldn't be read.")));
    return;
  }

  const notices = data.ratings_invalid ? invalidRatingsNotice(rerender) : null;
  show(back, heading, notices, promptStack(sessionId, data.prompts, rerender));
}

/* ---------- top rated (FR-007, FR-008, FR-009, FR-015) ---------- */

function topRatedCard(entry, reload, onInvalid) {
  if (entry.is_orphaned) {
    return el(
      "article",
      {},
      el("p", { class: "meta" }, el("span", { class: "score" }, String(entry.value)), el("span", { class: "badge" }, "Prompt unavailable")),
      el("p", { class: "muted" }, "The original prompt can't be found. Its session may have been moved or deleted.")
    );
  }
  const text = expandableText(entry.text, entry.is_truncated, async () => {
    const full = await api(
      "GET",
      `/api/sessions/${encodeURIComponent(entry.session_id)}/prompts/${encodeURIComponent(entry.prompt_id)}`
    );
    return full.text;
  });
  return el(
    "article",
    {},
    el(
      "p",
      { class: "meta" },
      el("span", { class: "score" }, String(entry.value)),
      el("span", {}, `Rated ${formatTime(entry.rated_at)}`),
      el("a", { href: `#/sessions/${encodeURIComponent(entry.session_id)}` }, "Open session")
    ),
    text,
    ratingControl({
      promptId: entry.prompt_id,
      sessionId: entry.session_id,
      position: entry.position,
      value: entry.value,
      onSaved: reload,
      onInvalid,
    })
  );
}

async function renderTopRated(page, token) {
  const heading = el("h2", {}, "Top rated");
  if (token === renderToken && !main.querySelector("article")) show(heading, el("p", { class: "muted" }, "Loading…"));
  let data;
  try {
    data = await api("GET", `/api/top-rated?page=${page}`);
  } catch (err) {
    if (token !== renderToken) return;
    if (err.payload && err.payload.ratings_invalid) show(heading, invalidRatingsNotice(() => route()));
    else show(heading, errorNotice(err));
    return;
  }
  if (token !== renderToken) return;

  if (data.prompts.length === 0) {
    show(
      heading,
      el(
        "div",
        { class: "notice" },
        el("p", {}, page > 1 ? "There are no more rated prompts." : "You haven't rated any prompts yet."),
        page > 1
          ? el("p", {}, el("a", { href: "#/top-rated" }, "Back to the first page"))
          : el("p", { class: "muted" }, "Open a session and rate a prompt to see it here.")
      )
    );
    return;
  }

  const reload = () => renderTopRated(page, ++renderToken);
  show(
    heading,
    data.prompts.map((entry) => topRatedCard(entry, reload, () => route())),
    pager("#/top-rated", data.page, data.has_more)
  );
}

/* ---------- favorite prompts ---------- */

function favoritePromptEditor({ heading, submitText, initialText = "", clearOnSuccess = false, onSubmit, onCancel }) {
  const textarea = el("textarea", {
    name: "text",
    rows: "8",
    placeholder: "Write a prompt you want to keep handy",
    "aria-label": heading,
  });
  textarea.value = initialText;
  const status = el("span", { class: "muted", role: "status" });
  const save = el("button", { type: "submit" }, submitText);
  const form = el(
    "form",
    { class: "editor" },
    el("h3", {}, heading),
    textarea,
    el(
      "div",
      { class: "actions" },
      save,
      onCancel ? el("button", { type: "button", onclick: onCancel }, "Cancel") : null,
      status
    )
  );
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const text = textarea.value;
    save.disabled = true;
    status.textContent = "Saving…";
    try {
      await onSubmit(text);
      if (clearOnSuccess) textarea.value = "";
      status.textContent = "Saved";
    } catch (err) {
      status.textContent = err.message;
    } finally {
      save.disabled = false;
    }
  });
  return form;
}

function favoritePromptCard(entry, reload) {
  let editing = false;
  const container = el("article", {});

  function render() {
    const meta = el(
      "p",
      { class: "meta" },
      el("span", {}, `Updated ${formatTime(entry.updated_at)}`),
      entry.updated_at !== entry.created_at ? el("span", {}, `Created ${formatTime(entry.created_at)}`) : null
    );
    if (editing) {
      container.replaceChildren(
        favoritePromptEditor({
          heading: "Edit favorite prompt",
          submitText: "Save changes",
          initialText: entry.text,
          onCancel: () => {
            editing = false;
            render();
          },
          onSubmit: async (text) => {
            await api("PUT", `/api/favorites/${encodeURIComponent(entry.favorite_prompt_id)}`, { text });
            reload();
          },
        })
      );
      return;
    }
    container.replaceChildren(
      meta,
      clampedText(entry.text),
      el(
        "div",
        { class: "actions" },
        el(
          "button",
          {
            type: "button",
            onclick: () => {
              editing = true;
              render();
            },
          },
          "Edit"
        )
      )
    );
  }

  render();
  return container;
}

async function renderFavorites(token) {
  const heading = el("h2", {}, "Favorite prompts");
  show(heading, el("p", { class: "muted" }, "Loading…"));
  let data;
  try {
    data = await api("GET", "/api/favorites");
  } catch (err) {
    if (token !== renderToken) return;
    if (err.payload && err.payload.favorites_invalid) {
      show(heading, invalidFavoritesNotice(() => route()));
    } else {
      show(heading, errorNotice(err));
    }
    return;
  }
  if (token !== renderToken) return;

  const reload = () => renderFavorites(++renderToken);
  const createForm = favoritePromptEditor({
    heading: "Add a favorite prompt",
    submitText: "Save prompt",
    clearOnSuccess: true,
    onSubmit: async (text) => {
      await api("POST", "/api/favorites", { text });
      reload();
    },
  });

  show(
    heading,
    el("p", { class: "muted" }, "Save your own prompt drafts here and edit them inline."),
    createForm,
    data.prompts.length
      ? [...data.prompts.map((entry) => favoritePromptCard(entry, reload))]
      : el(
          "div",
          { class: "notice" },
          el("p", {}, "You haven't saved any favorite prompts yet."),
          el("p", { class: "muted" }, "Use the form above to add prompts you want to reuse later.")
        )
  );
}

/* ---------- routing ---------- */

function route() {
  const token = ++renderToken;
  const hash = location.hash || "#/sessions";
  const [path, query] = hash.slice(1).split("?");
  const params = new URLSearchParams(query || "");
  const page = Math.max(1, parseInt(params.get("page"), 10) || 1);
  const search = (params.get("q") || "").trim();
  const parts = path.split("/").filter(Boolean);

  const onTopRated = parts[0] === "top-rated";
  const onFavorites = parts[0] === "favorites";
  const setCurrent = (id, active) =>
    active ? document.getElementById(id).setAttribute("aria-current", "page") : document.getElementById(id).removeAttribute("aria-current");
  setCurrent("nav-top-rated", onTopRated);
  setCurrent("nav-favorites", onFavorites);
  setCurrent("nav-sessions", !onTopRated && !onFavorites);

  window.scrollTo(0, 0);
  if (onTopRated) return renderTopRated(page, token);
  if (onFavorites) return renderFavorites(token);
  if (parts[0] === "sessions" && parts[1]) return renderSessionDetail(decodeURIComponent(parts[1]), token);
  if (search) return renderPromptSearch(search, page, token);
  return renderSessionList(page, token);
}

window.addEventListener("hashchange", route);
route();
