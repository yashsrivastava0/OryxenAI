# Shared image retrieval

Build Preparation and Code Generator use the same provider-neutral image
service in `agents/shared/image_retrieval.py`:

```text
approved portfolio context
  -> structured intent and up to three concise queries
  -> Pexels first, Pixabay fallback (both for important imagery)
  -> cached metadata search and deterministic ranking
  -> download only the selected HTTPS rendition
  -> decode, validate, crop, resize, compress, hash
  -> local build-context or Code Generator material
```

The default provider order is `pexels`, then `pixabay`. Pixabay rendition
selection tolerates missing full-access fields and uses the best available
`imageURL`, `fullHDURL`, `largeImageURL`, or `webformatURL`. Search responses
are cached for 24 hours in `.workspace/image-search-cache`; credentials are
never written to cache files. The worker and detached Build Preparation
container share that cache volume in Docker.

Unsplash remains a tertiary adapter only when both
`unsplash_enabled` and `unsplash_local_vendoring_authorized` are explicitly
enabled. It is never a browser-runtime source. Component retrieval is a
separate cache-free path and is not changed by this feature.

Every materialized image is decoded and pixel-inspected, checked for minimum
dimensions and approved HTTPS hosts, content-addressed, and accompanied by
provider, source page, author, license, dimensions, crop, and hash metadata.

Provider references:

- [Pixabay API](https://pixabay.com/api/docs/)
- [Pixabay license](https://pixabay.com/service/license-summary/)
- [Pexels API](https://www.pexels.com/api/documentation/)
- [Pexels license](https://www.pexels.com/legal-pages/license/)
