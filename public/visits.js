// Load once per page visit, on the published site only. No polling: requesting
// the badge records a hit, so refreshing it on a timer would inflate the total.
const isPublishedSite = location.hostname === "sean-p-clohessy.github.io"
  && location.pathname.startsWith("/CPD-Finder/");
const counter = document.querySelector("#visit-counter");
const badge = document.querySelector("#visit-badge");

if (isPublishedSite && counter && badge) {
  counter.hidden = false;
  badge.addEventListener("load", () => { badge.alt = "CPD Finder total visits — open for details"; }, { once: true });
  badge.src = "https://hits.sh/sean-p-clohessy.github.io/CPD-Finder.svg?label=Visits&color=6950d8&labelColor=201946";
}
