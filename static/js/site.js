(function () {
  const root = document.documentElement;
  const storageKey = "blog-theme";
  const button = document.querySelector("[data-theme-toggle]");
  const savedTheme = localStorage.getItem(storageKey);
  const systemPrefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const initialTheme = savedTheme || (systemPrefersDark ? "dark" : "light");

  root.dataset.theme = initialTheme;

  if (button) {
    button.textContent = initialTheme === "dark" ? "浅色模式" : "深色模式";
    button.addEventListener("click", function () {
      const nextTheme = root.dataset.theme === "dark" ? "light" : "dark";
      root.dataset.theme = nextTheme;
      localStorage.setItem(storageKey, nextTheme);
      button.textContent = nextTheme === "dark" ? "浅色模式" : "深色模式";
    });
  }
})();
