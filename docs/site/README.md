# Website sources

The team website, <https://promaaa.github.io/vision-sobang/>, is built from these files.
The pages, images and videos are in the `gh-pages` branch of this repository.

| File | What |
| --- | --- |
| `index.src.html` | Main page ("Firefighter robot"). `bom.py` and `build.sh` fill in the parts list and the software diagram |
| `bom.py` | Writes the parts list table, in English, from `docs/hardware/bom_extinction.csv` |
| `diagram.txt` | The software diagram (plain text) |
| `concepts.py` | Writes the "Body concepts" page |
| `wiki.css` | The style, after the Arch Wiki |
| `build.sh` | Builds both pages into a checkout of the site |

## Update the website

1. Check out the `gh-pages` branch next to this folder once, from the repository root:

```bash
git worktree add ../vision-sobang-site gh-pages
```

2. Build the pages:

```bash
docs/site/build.sh ../vision-sobang-site
```

3. Open `../vision-sobang-site/index.html` in a browser and check the pages.
4. Copy new images or videos into `../vision-sobang-site/`, then commit and push there. GitHub Pages updates the site in about 1 minute.
