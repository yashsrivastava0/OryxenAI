# Motion research applied to the three portfolio concepts

The previews use browser-native CSS with functional static states. No animation is required to read the content or follow a link.

| Pattern | Applied in the prototypes | Primary reference |
| --- | --- | --- |
| Scroll and view timelines | Reading progress, subtle art movement, and entrance effects; each is inside `@supports` and reduced-motion rules | [Chrome for Developers: Scroll-driven animations](https://developer.chrome.com/docs/css-ui/scroll-driven-animations), [WebKit: Scroll-driven animations](https://webkit.org/blog/17101/a-guide-to-scroll-driven-animations-with-just-css/) |
| Parallax inside a stable frame | Decorative layers move while the project frame keeps its size, following the developer demo's approach to avoid changing scroll geometry | [Scroll-driven Animations: Parallax Carousel](https://scroll-driven-animations.style/demos/parallax-carousel/css/), [Stacking Cards](https://scroll-driven-animations.style/demos/stacking-cards/css/) |
| Cross-document transitions | Each page opts in with `@view-transition { navigation: auto; }`. Shared names are assigned only to unique elements; ordinary links remain the fallback. | [Chrome for Developers: Cross-document view transitions](https://developer.chrome.com/docs/web-platform/view-transitions/cross-document), [MDN: `@view-transition`](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/%40view-transition) |
| Motion restraint | Ambient shapes use low-opacity color and transform; interactive content stays legible. Reduced-motion users receive static artwork and immediate navigation. | [MDN: CSS performance](https://developer.mozilla.org/en-US/docs/Learn_web_development/Extensions/Performance/CSS), [WebKit: Responsive design for motion](https://webkit.org/blog/7551/responsive-design-for-motion/) |

Each theme has a distinct motion vocabulary: Editorial Forest uses slow ink and topographic drift; Obsidian Signal uses plasma, hard-edged movement, and square controls; Cobalt Atlas uses soft liquid shapes, circular parallax, and radial controls. The websites are static multi-page HTML previews. The production Studio theme and its one-page contract remain unchanged.
