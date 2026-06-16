(async function () {
  const input = document.getElementById("search-input");
  const container = document.querySelector("[data-search-results]");

  if (!input || !container) {
    return;
  }

  const baseUrl = document.documentElement.dataset.baseUrl || "";
  const response = await fetch(baseUrl + "/search.json");
  const records = await response.json();

  function render(items) {
    if (!items.length) {
      container.innerHTML = '<p class="empty-state">没有找到匹配内容，换个关键词试试。</p>';
      return;
    }

    container.innerHTML = items
      .map(function (item) {
        const tags = (item.tags || []).map(function (tag) {
          return '<span class="tag">#' + tag + "</span>";
        }).join("");

        return [
          '<article class="search-item">',
          '<div class="card-meta"><span>' + item.kind + "</span>",
          item.category ? '<span>' + item.category + "</span>" : "",
          "</div>",
          '<h2><a href="' + baseUrl + item.url + '">' + item.title + "</a></h2>",
          "<p>" + item.summary + "</p>",
          '<div class="tag-row">' + tags + "</div>",
          "</article>",
        ].join("");
      })
      .join("");
  }

  input.addEventListener("input", function () {
    const keyword = input.value.trim().toLowerCase();
    if (!keyword) {
      container.innerHTML = '<p class="empty-state">输入关键词后，结果会显示在这里。</p>';
      return;
    }

    const matches = records.filter(function (item) {
      return [item.title, item.summary, item.content, item.category, (item.tags || []).join(" ")]
        .join(" ")
        .toLowerCase()
        .includes(keyword);
    }).slice(0, 20);

    render(matches);
  });
})();
