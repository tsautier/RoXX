const tabs = [...document.querySelectorAll('[role="tab"]')];
const menuButton = document.querySelector(".menu-toggle");
const navigation = document.querySelector(".site-nav");

function activateTab(tab, focus = false) {
  for (const item of tabs) {
    const selected = item === tab;
    item.setAttribute("aria-selected", String(selected));
    item.tabIndex = selected ? 0 : -1;
    document.getElementById(item.getAttribute("aria-controls")).hidden =
      !selected;
  }
  if (focus) tab.focus();
}

tabs.forEach((tab, index) => {
  tab.addEventListener("click", () => activateTab(tab));
  tab.addEventListener("keydown", (event) => {
    const next =
      event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (!next && event.key !== "Home" && event.key !== "End") return;
    event.preventDefault();
    const target =
      event.key === "Home"
        ? tabs[0]
        : event.key === "End"
          ? tabs[tabs.length - 1]
          : tabs[(index + next + tabs.length) % tabs.length];
    activateTab(target, true);
  });
});

menuButton.addEventListener("click", () => {
  const open = menuButton.getAttribute("aria-expanded") !== "true";
  menuButton.setAttribute("aria-expanded", String(open));
  menuButton.setAttribute(
    "aria-label",
    open ? "Close navigation" : "Open navigation",
  );
  navigation.classList.toggle("open", open);
});
navigation.querySelectorAll("a").forEach((link) =>
  link.addEventListener("click", () => {
    menuButton.setAttribute("aria-expanded", "false");
    menuButton.setAttribute("aria-label", "Open navigation");
    navigation.classList.remove("open");
  }),
);

document.querySelectorAll("[data-copy]").forEach((button) => {
  button.addEventListener("click", async () => {
    const code = document.querySelector(
      "#commands-" + button.dataset.copy + " code",
    ).textContent;
    try {
      await navigator.clipboard.writeText(code);
      button.textContent = "Copied";
      window.setTimeout(() => {
        button.textContent = "Copy";
      }, 1800);
    } catch {
      button.textContent = "Select text";
      window.setTimeout(() => {
        button.textContent = "Copy";
      }, 1800);
    }
  });
});

fetch("https://api.github.com/repos/tsautier/RoXX/releases/latest", {
  headers: { Accept: "application/vnd.github+json" },
})
  .then((response) => {
    if (!response.ok) throw new Error("Release metadata unavailable");
    return response.json();
  })
  .then((release) => {
    if (!release.tag_name || !Array.isArray(release.assets)) return;
    document.querySelectorAll("[data-release-version]").forEach((item) => {
      item.textContent = release.tag_name;
    });
    document.querySelectorAll("[data-release-page]").forEach((item) => {
      item.href = release.html_url;
    });
    for (const link of document.querySelectorAll(
      "[data-asset], [data-asset-pattern]",
    )) {
      const asset = release.assets.find((item) =>
        link.dataset.asset
          ? item.name === link.dataset.asset
          : item.name.startsWith(link.dataset.assetPattern) ||
            item.name.endsWith(link.dataset.assetPattern),
      );
      if (asset) link.href = asset.browser_download_url;
    }
    const mac = release.assets.find((item) =>
      /^roxx-macos-(arm64|x86_64)$/.test(item.name),
    );
    if (mac) {
      const code = document.querySelector("#commands-macos code");
      code.textContent = code.textContent.replaceAll(
        "roxx-macos-arm64",
        mac.name,
      );
    }
  })
  .catch(() => {
    // Static links still take visitors to the latest release if the API is unavailable.
  });
