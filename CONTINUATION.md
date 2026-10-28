# Project Handoff / Continuation File

Paste this file (or point your AI tool at it) to continue the project without
the earlier conversation. It is self-contained: sections 1-10 explain the
project, section 11 lists every file, section 12 describes the review
documents (decks and PDFs), section 13 explains how to recreate the code, and
Appendix A contains the full source of every code file. Appendix B has the
generator for the test dataset.

**AI tool quick start:** run the restore script in section 13 to recreate the
project, `pip install -r requirements.txt`, then `python app.py` or
`python cli.py sample_200.csv`. Read sections 4 and 7 before changing code.

> Keep this file OUT of the public GitHub repo, or trim it first: it contains
> local paths and the author's working notes. It is currently untracked.

## 1. What the project is

**Automated Data Health & Profiling Dashboard.** Given any CSV, it:

1. Reports statistics on the raw data: dtypes, missing counts, mean, median,
   mode, variance, std dev, kurtosis, five-point summary, covariance matrix.
2. Fills missing numeric values (median by default, or KNN imputation) in a
   *working copy* used only for scoring.
3. Flags multivariate outliers with two unsupervised detectors,
   **Isolation Forest** and **KNN-distance**, each with a plain-language
   `why_flagged` reason per row, and compares the two.
4. Shows a per-cell comparison of median fill vs KNN fill.

It exists as a **CLI** (`cli.py`) and a **Flask web UI** (`app.py` + `static/`)
that share exactly the same core modules. It is a university AIML course
project (final review stage). The original roadmap said "Streamlit"; the web
UI was built with Flask + plain HTML/JS instead so it can deploy on Vercel.

## 2. Where everything is

- Local folder: `E:\semester 3\AIML project` (Windows 11, Python 3.11.8)
- GitHub: https://github.com/Kamalesh974/automated-data-health-dashboard
  (public, branch `main`, one commit `bae8e48`, pushed and in sync)
- Git identity is already configured globally. User wants **no Co-Authored-By
  line and no Claude/bot collaborator** on commits or the repo.

Tracked in the repo (code, UI, README, samples only):

```
cli.py              CLI entry point (argparse + printing only)
stats.py            descriptive statistics (pure functions)
preprocessing.py    impute_numeric_median, impute_numeric_knn, compare_imputations
ml_processing.py    Isolation Forest + KNN detectors, comparison, shared prep
app.py              Flask app; imports the modules above unchanged
static/             index.html, style.css, app.js, samples/*.csv
sample_*.csv        4 test fixtures (numeric, messy, fully_missing_col, 200)
requirements.txt    pandas numpy scikit-learn tabulate flask
vercel.json  .python-version (3.12)  .gitignore  README.md
```

Untracked on purpose (personal review documents; contain teammates' names and
roll numbers; do not push): `Abstract for AIML.pdf`, `Work_Completed.pdf`,
`Remaining_Work_For_Completion.pdf`, `Project_Summary_Simple.pdf`,
`Demo_QA_Cheatsheet.pdf`, `Mid_Review_Progress.pptx`,
`Project_Report_Presentation.pptx`, `Project_Presentation_Simple.pptx`.

## 3. How to run

```bash
pip install -r requirements.txt

# CLI
python cli.py sample_200.csv                                  # both methods + comparison
python cli.py sample_200.csv --method knn --k 7
python cli.py sample_200.csv --method isolation_forest --impute-method knn --impute-k 5
python cli.py sample_200.csv --contamination 0.1
python cli.py sample_200.csv --no-impute

# Web UI
python app.py          # then open http://localhost:5000
```

CLI flags: `--method {isolation_forest,knn,both}` (default both),
`--contamination` (0 < x <= 0.5, default 0.05, used by both detectors),
`--k` (outlier-detector KNN neighbours, default 5), `--no-impute`,
`--impute-method {median,knn}` (default median), `--impute-k` (KNN-imputer
neighbours, default 5). Invalid values give an argparse usage error.

Windows gotchas: use `PYTHONUTF8=1` when printing non-ASCII from Python;
`pip` may not be on PATH, use `python -m pip`.

## 4. Design decisions you must preserve

- **Statistics are computed on RAW data.** Imputation happens only in a working
  copy right before scoring. Do not impute before computing stats.
- **Two different "KNN"s.** `detect_outliers_knn` scores rows by distance to the
  k-th nearest neighbour (on standardised features) and flags the top
  `contamination` fraction. `impute_numeric_knn` uses sklearn `KNNImputer` to
  fill gaps. They have independent neighbour counts (`k` vs `impute_k`). The
  detector's imputation is a separate choice (`impute_method`).
- `_prepare_scoring_data` always computes BOTH median and KNN imputations when
  `impute=True`, only to build `imputation_comparison`; only the chosen one is
  used for scoring.
- Fully-empty numeric columns are dropped from scoring and reported (no median
  or neighbours exist). Mixed-type columns are non-numeric (pandas dtype).
- Isolation Forest: `random_state=42`, 100 trees, flagged via
  `predict == -1`; score = `score_samples` (more negative = more anomalous);
  threshold = `model.offset_`. KNN is deterministic.
- `why_flagged` is an approximation: the 2 columns with largest |z-score| vs
  that column's mean/std. Neither model gives real per-feature reasoning.
- pandas treats `"n/a"`, `"NA"`, `"null"`, etc. as missing, so such cells do not
  make a column non-numeric. The browser preview parser mirrors this list.
- Web UI never duplicates logic; it calls the same functions as the CLI.

## 5. Web API contract

`POST /api/analyze` (multipart): `file`, `method`, `contamination`, `k`,
`impute` ("true"/"false"), `impute_method`, `impute_k`. Errors are
`{"error": "..."}` with 400/413. Response keys: `rows`, `columns`,
`columns_info`, `has_numeric`, and when numeric: `numeric_summary`,
`five_point_summary`, `covariance_matrix`, `raw_numeric` (+
`raw_numeric_truncated`, capped at 3000 rows for charts), `results`
(per detector: counts, `flagged` table, `model_settings`, `impute_method`),
`flagged_by` (row index -> both/isolation_forest/knn),
`imputation_comparison` (only when imputing and there are gaps), `comparison`
(only when both methods ran). Tables are `{columns, rows}` with `_index`.
`GET /api/health` returns `{"status":"ok"}`. Upload cap `MAX_CONTENT_LENGTH`
= 1 GB.

UI features: dark mode (OS default, toggle saved in localStorage), sortable
tables + CSV export, scatter (coloured by flagging method), histogram,
anomaly-score bars with threshold line, instant client-side box plot per numeric
column on file selection (small multiples, own scale each), imputation
comparison table. Chart.js 4.4.4 and chartjs-chart-boxplot loaded from
jsdelivr CDN; Inter / JetBrains Mono from Google Fonts.

## 6. Verified results (sample_200.csv)

Synthetic: 200 rows, 6 cols, ~37 missing cells, 8 planted multivariate outliers
at row ids **3, 31, 39, 104, 145, 171, 190, 192** (the ground truth). With
contamination 0.05 (10 rows flagged per method):

| Setup | Planted found |
|---|---|
| Isolation Forest, median fill | 7/8 (misses id 145; extras 12, 22, 117) |
| Isolation Forest, KNN fill | 8/8 (extras 12, 22) |
| KNN detector, either fill | 8/8 (extras 22, 141) |

Both methods flag 8 rows in common; 12 distinct; rank correlation 0.862;
agreement 67%. At contamination 0.10 both methods find 8/8. Id 145 is missed
with median fill because its income/score were blanked and the median made it
look normal. These are a controlled test, not a real-data guarantee.

Earlier in the project an incorrect "8/8 for Isolation Forest" figure was
reported (an evaluation script dropped a column). It was caught and corrected;
the table above is the correct one. Always recompute against the CSV on disk.

Testing so far is manual (CLI runs on all 4 CSVs and edge cases: no numeric
columns, 1-row file, all-missing column, k larger than rows, bad args; API
error paths; browser checks). **There is no automated test suite.**

## 7. Known limitations

- 1 GB upload cap only applies locally. Vercel enforces a much smaller request
  body limit, and huge files make IsolationForest / NearestNeighbors very slow
  or memory-heavy. Reading is not chunked.
- No categorical encoding, no feature scaling for Isolation Forest (KNN
  standardises its own copy), no result export beyond per-table CSV in the UI.
- Vercel bundle: pandas + numpy + scikit-learn is about 400 MB of a 500 MB
  limit. Fallback: `VERCEL_SUPPORT_LARGE_FUNCTIONS=1`. Untested.
- The Flask dev server (`debug=True`) is not for production; use gunicorn or
  Vercel's runtime. In the Claude Code environment, background processes are
  killed after a time limit; run `python app.py` in your own terminal.
- Cross-method comparison only has two methods; no Local Outlier Factor.

## 8. Remaining to-do (in priority order)

1. **Deploy to Vercel** (user said "later"): import the GitHub repo at
   vercel.com/new; Vercel detects Flask from `requirements.txt` + `app.py`.
   Check bundle size on first build.
2. **Refresh the review documents** (stale): the 3 decks and 4 PDFs do not yet
   mention KNN imputation, the Isolation Forest 7/8 -> 8/8 improvement with KNN
   fill, the box plot / UI, or the 1 GB limit. `Project_Report_Presentation.pptx`
   and `Project_Presentation_Simple.pptx` were edited in place with python-pptx;
   the PDFs were generated with reportlab and must be regenerated.
3. Fill placeholders in decks/PDFs: `[Your Name]`, `[Course Name]`,
   `[Guide / Mentor Name]`, `[Review Date]`, `[Role / Roll Number]`,
   `[Institution Name]`. Team details are in `Abstract for AIML.pdf`.
4. Visually check the edited slides in PowerPoint (no renderer was available
   on this machine, so only text/structure were verified).
5. Add pytest tests for `stats.py`, `preprocessing.py`, `ml_processing.py`
   (including the planted-outlier recall check above).
6. Optional: README polish, scale numeric columns before Isolation Forest, add
   LOF, an export-report feature.
7. Rebuild the restyled navy/Arial report deck and the MSA-style 15-slide deck
   (neither is in the project folder; see section 12.2).
8. Copy the project folder somewhere safe: no backups of the decks or PDFs
   exist and the generator scripts were deleted.

## 9. Gotchas learned the hard way

- python-pptx / the pptx validator on Windows need `PYTHONUTF8=1`.
- No LibreOffice or Poppler on this machine; cannot render slides to images.
- Windows console prints non-ASCII as `?`; inspect codepoints, do not trust the
  display.
- `pd.read_csv` silently converts `"n/a"` to NaN.
- pandas 3.x is strict about assigning strings into float columns.
- reportlab has a built-in style named `Code`; use another name. Wrap table
  cells in `Paragraph` or long cells overlap.
- When testing the UI by script, re-query the DOM after a table re-renders
  (`drawTable` replaces `innerHTML`), or you read a stale detached table.
- Browser-pane screenshots are scaled; click by element ref, not coordinates.

## 10. Working preferences of the user

- Wants honest, verified numbers; ask before publishing anything external.
- No Co-Authored-By line, no Claude collaborator on GitHub.
- Decks: plain/simple English when asked, "humanoid" (not obviously
  AI-templated) look, no more than 14 slides in the simple deck, recent
  real papers cited (three verified: Cao et al. 2025 *Machine Intelligence
  Research*; Zhou et al. 2024 IEEE AITest; Kampf et al. 2025 *PLOS ONE*).
- Never fabricate citations or results; recompute against the data on disk.

## 11. Complete file inventory

Sizes are bytes at the time of writing. "Repo" = tracked and pushed to GitHub.

| Path | Bytes | Repo | What it is / how it was made |
|---|---|---|---|
| `cli.py` | 8738 | yes | CLI entry point. argparse, printing with `tabulate` (falls back to `DataFrame.to_string`), calls the modules below. Handwritten Python. |
| `stats.py` | 1586 | yes | `dataset_overview`, `numeric_summary`, `five_point_summary`, `covariance_matrix`. Pure functions, no printing. |
| `preprocessing.py` | 3544 | yes | `impute_numeric_median`, `impute_numeric_knn`, `compare_imputations`. |
| `ml_processing.py` | 10599 | yes | `get_numeric_columns`, `detect_outliers_isolation_forest`, `detect_outliers_knn`, `compare_outlier_methods`, plus private helpers. |
| `app.py` | 7992 | yes | Flask backend. Imports the modules above unchanged. Serves `static/`. |
| `static/index.html` | 5157 | yes | Single page. Loads Chart.js 4.4.4 and chartjs-chart-boxplot from jsdelivr, fonts from Google Fonts. |
| `static/style.css` | 12020 | yes | CSS variables, dark theme (`[data-theme]` + `prefers-color-scheme`), responsive breakpoint at 640px. |
| `static/app.js` | 26993 | yes | All frontend logic: theme, file handling, instant box-plot preview, sortable/exportable tables, charts, analyze call. No framework, no build step. |
| `static/samples/*.csv` | 309 / 531 / 6843 | yes | Copies of `sample_numeric.csv`, `sample_messy.csv`, `sample_200.csv` for the UI's "try a sample" buttons. Keep in sync with the root copies. |
| `sample_numeric.csv` | 309 | yes | 15 rows, clean numeric, a few blanks. |
| `sample_messy.csv` | 531 | yes | 16 rows, mixed types and blanks. Only `score` ends up numeric (other columns contain stray text such as "abc"). |
| `sample_fully_missing_col.csv` | 71 | yes | 5 rows, one entirely empty numeric column `ghost_col`. |
| `sample_200.csv` | 6843 | yes | Synthetic evaluation set; generated by `gen_sample_200.py` in Appendix B (reproduces it byte-for-byte). |
| `requirements.txt` | 41 | yes | `pandas numpy scikit-learn tabulate flask` (unpinned). |
| `vercel.json` | 190 | yes | Excludes `__pycache__`, `.git`, `.claude`, `*.md` from the function bundle. |
| `.python-version` | 5 | yes | `3.12` (Vercel). Local Python is 3.11.8. |
| `.gitignore` | 67 | yes | Python caches, venvs, `.vercel`, `.env`. |
| `README.md` | 5642 | yes | Public project README. |
| `CONTINUATION.md` | this file | no | This handoff. Contains local paths; do not push as is. |
| `Abstract for AIML.pdf` | 105195 | no | The user's own abstract (Group 18, four students). Not made by the assistant. Contains names and roll numbers. |
| `Work_Completed.pdf` | 22517 | no | 8-page plain-language guide to the whole tool (see section 12). |
| `Remaining_Work_For_Completion.pdf` | 5722 | no | 2-page remaining-work list, updated to show what is done. |
| `Project_Summary_Simple.pdf` | 7587 | no | 3-page "in simple words" summary. |
| `Demo_QA_Cheatsheet.pdf` | 4320 | no | One-page demo commands + 9 anticipated review questions. Must stay on ONE page. |
| `Mid_Review_Progress.pptx` | 63046 | no | 13 slides, teal palette, speaker notes. Early demo deck; never updated afterwards. |
| `Project_Report_Presentation.pptx` | 73029 | no | 19 slides following the course rubric (i to viii). See caveat in section 12. |
| `Project_Presentation_Simple.pptx` | 49894 | no | 14 slides, plain English, three literature-review slides. |

NOT in the project folder (see section 12): the restyled navy/Arial version of
the report deck and the MSA-style 15-slide deck.

**There are no backups.** The assistant's scratch folders that held generator
scripts and original copies of the documents have been deleted. The PDFs and
decks in the project folder are the only copies. Copy the whole folder
somewhere safe.

## 12. The review documents in detail

### 12.1 Reference material the user supplied (style models, not part of this project)

- `E:\semester 3\ROBOTIC\slides\PINN_IK_Mid_Review.pptx` and its generator
  `generate_deck.js` (pptxgenjs). Style: navy `1E2761`, black, gray `444444`,
  light tint `EEF1F8`, Arial everywhere, "SECTION N" kicker above a bold navy
  title, numbered navy circles for step lists, rounded boxes joined by arrow
  shapes, navy-header tables with `D9D9D9` borders, native bar/line charts,
  centered title and "Thank You" slides, no page numbers.
- `C:\Users\gkama\Downloads\MSA Mid review.pptx` (a different group project:
  bond-graph PINNs). Style: cream background `F4EDE2`, navy text `303870` only
  (no black), titles in "Agrandir Wide Bold" (all caps), body in "Nunito" /
  "Nunito Bold", both fonts embedded in that file. 15-slide structure: Title
  with group and members, Table of Content as a 2-column grid of outlined
  rounded cards, Introduction, Motivation, Problem Statement, Objectives
  (Primary / Secondary columns), Literature Review (a pasted image),
  Technical Explanation (bold term: explanation), Overall Methodology
  (vertical line with dots and left label / right explanation), Results x2
  (images), Challenges (3 columns), Conclusion, Future Work, Thank You. A
  right-edge navy freeform shape is on every slide.

### 12.2 The three decks in the folder

**`Mid_Review_Progress.pptx` (13 slides).** pptxgenjs, palette 028090 / 00A896 /
02C39A with a dark `0B2027` for title and closing slides, fonts Cambria and
Calibri, speaker notes on every slide. Slides: Title; Agenda; Goal and scope;
Tech stack; Phase 1 statistics; Phase 2 Isolation Forest; How Isolation
Forest works (crowded-room analogy); Bonus median imputation; Program flow
(boxes and arrows); Live demo (terminal-style output); Progress 50% (progress
bar); What's left; Thank you. Written before KNN existed. Leave as history.

**`Project_Report_Presentation.pptx` (19 slides).** Follows the course rubric:
i Introduction and motivation; ii Problem statement and relevance;
iii Objectives and scope; iv Methodology with 8 sub-items (1 dataset,
2 representation/preprocessing, 3 EDA/visualisation, 4 algorithm selection,
5 training and validation, 6 evaluation metrics, 7 comparison of alternatives,
8 software implementation); v Results; vi Conclusion and future work;
vii References; viii Contributors. Slide order: 1 Title, 2 Outline, 3 i, 4 ii,
5 iii, 6 iv overview, 7 iv.1, 8 iv.2, 9 iv.3, 10 iv.4, 11 iv.5, 12 iv.6
(metrics table), 13 iv.7 (comparison table), 14 workflow diagram (6 boxes, with
speaker notes), 15 iv.8, 16 v, 17 vi, 18 vii, 19 viii.
- **Caveat:** the file in the folder is the OLDER style (Cambria headers,
  Calibri body, kickers like "III. OBJECTIVES & SCOPE", plain tables). A newer
  navy/Arial restyle (reference-deck look, numbered circles, arrow-box
  workflow, a real bar chart on slide 12) was built and sent to the user from
  a temporary folder, but never copied into the project folder.
- It was edited in place with python-pptx (41 text edits) to say: two ML
  methods, KNN implemented, Isolation Forest 7/8 vs KNN 8/8 at 0.05, both agree
  on 8 (12 distinct), rank correlation 0.86; title slide says "Final Review
  Presentation" and `[Review Date]`. It does NOT yet mention KNN imputation.
- Placeholders still present: `[Course Name]`, `[Guide / Mentor Name]`,
  `[Your Name]`, `[Review Date]`, `[Role / Roll Number]`, `[Institution Name]`.

**`Project_Presentation_Simple.pptx` (14 slides).** Plain look: Arial, white,
navy headings, bullets, two small tables. Slides: Title; Introduction; Problem;
Objectives; What we built; How it works; Related Work 1, 2, 3 (one paper per
slide); Results (table with separate Isolation Forest and KNN rows); What's
left; Conclusion; References; Contributors. Edited in place (13 text edits) for
KNN. An "elaborated" 14-slide variant (extra slides explaining ML and
Isolation Forest, and the three papers merged into ONE table slide) was built
and validated in a temporary folder but never delivered; rebuild it if wanted.

**The MSA-style deck** (15 slides, `Project_Presentation_MSA_Style.pptx`): built
and sent to the user but not in the project folder. Its builder script is gone.
Content mapped the Data Health project onto the MSA structure, with a Challenges
slide taken from real problems (console encoding, pandas `"n/a"` handling,
evaluating an unsupervised model without ground truth). Fonts "Agrandir Wide
Bold" / "Nunito" are not installed system-wide, so PowerPoint substitutes them
unless the user installs them or embeds fonts when saving.

### 12.3 Literature review used in the decks (three papers, verified online)

1. Cao, Xiang, Zhang, Zhu, Ting (2025). *Anomaly Detection Based on Isolation
   Mechanisms: A Survey.* Machine Intelligence Research (arXiv 2403.10802).
   Gap used: no focus on explaining why a specific row was flagged.
2. Zhou, Tu, Sha, Ding, Chen (2024). *A Survey on Data Quality Dimensions and
   Tools for Machine Learning.* IEEE AITest 2024, pp. 120-131 (arXiv 2406.19614).
   Reviews 17 data-quality tools; calls for more open-source tools.
3. Kampf, Dykun, Rassaf, Mahabadi (2025). *A comparison of various imputation
   algorithms for missing data.* PLOS ONE 20(5): e0319784. Compares five
   MICE-family methods; predictive mean matching best; simple methods such as
   median not tested.

Other citations in the decks: Liu, Ting, Zhou (2008) Isolation Forest, IEEE ICDM
413-422; Ramaswamy, Rastogi, Shim (2000) Efficient algorithms for mining
outliers from large data sets, ACM SIGMOD 427-438; Pedregosa et al. (2011)
scikit-learn, JMLR 12:2825-2830; Harris et al. (2020) NumPy, Nature 585:357-362;
pandas (McKinney et al.). Do not invent further citations; verify any new one.

### 12.4 The PDFs

All four were produced with Python **reportlab** (platypus: `SimpleDocTemplate`,
`Paragraph`, `Table`, `ListFlowable`, `KeepTogether`, plus
`reportlab.graphics.shapes` for the flow diagram). Original generator scripts
are gone. To regenerate, follow these rules that fixed real bugs:
- Wrap every table cell in a `Paragraph`; raw strings overlap when long.
- Do not name a style `Code` (reserved); do not use Unicode sub/superscripts.
- Escape `&` as `&amp;` in Paragraph text; use `-` rather than HTML bullets.
- Letter size, 0.8in side margins, dark `1a1a2e` table headers, `f7f7fb`
  alternate rows. The cheat sheet uses tighter margins to stay at one page.
- Verify with `pdfplumber` (page count, no `(cid:` or garbled text).

Contents: `Work_Completed.pdf` = (1) what it does, (2) tools explained, (3) files,
(4) each statistic explained, (5) both models with analogies (crowded room for
Isolation Forest, "distance to fifth-closest neighbour" for KNN) and why use
both, (6) median imputation, (7) a 10-step flow diagram plus walkthrough,
(8) how to run, (9) testing, (10) results table, (11) acceptance checklist.
`Remaining_Work_For_Completion.pdf` = completed list, deferred items, Streamlit
integration, preprocessing, export, testing, future ideas, documentation.
`Project_Summary_Simple.pdf` = 7 short sections, plain words.
`Demo_QA_Cheatsheet.pdf` = demo commands, 9 Q and A, key numbers.
All four were last updated 2026-09-26 and predate KNN imputation, the web UI,
and the 1 GB limit.

### 12.5 Tooling used to build and check documents

pptxgenjs (npm) for new decks (use `LAYOUT_WIDE` 13.33 x 7.5 in; hex colours
without `#`; `bullet: true`; never reuse option objects; `rectRadius` only on
`roundRect`; run the validator afterwards). python-pptx for in-place edits
(preserve formatting by editing `run.text`, never `text_frame.text`). Skill
validator: `PYTHONUTF8=1 python <skills>/pptx/scripts/office/validate.py deck.pptx`.
`python -m markitdown deck.pptx` for a text dump. No LibreOffice, so slides
cannot be rendered to images on this machine.

## 13. How to recreate the code files

**Option A, restore verbatim.** Appendix A below contains every code file
exactly as it is on disk, each under a `### FILE: path` heading inside a
five-backtick fence. This script extracts them all (run it in an empty
folder, with this file saved as `CONTINUATION.md`):

```python
import re, pathlib
text = open("CONTINUATION.md", encoding="utf-8", newline="").read()  # keep \r\n
pattern = re.compile(r"^### FILE: ([^\n]+)\n+`{5}[^\n]*\n(.*?)\n`{5}$", re.M | re.S)
for path, body in pattern.findall(text):
    p = pathlib.Path(path.strip())
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8", newline="")
    print("wrote", p)
```

Then copy `sample_numeric.csv`, `sample_messy.csv` and `sample_200.csv` into
`static/samples/`, run `pip install -r requirements.txt`, then `python app.py`.

**Option B, regenerate from this specification** (if you prefer to rewrite):

- `stats.py`: `dataset_overview(df) -> {rows, columns, columns_info}` where
  `columns_info` is a DataFrame of `dtype` (string) and `missing`;
  `numeric_summary(numeric_df)` one row per column with mean, median, mode (first
  mode or NaN), variance, std_dev, kurtosis (pandas `.kurt()`), computed on
  `dropna()`; `five_point_summary` min, Q1, median, Q3, max;
  `covariance_matrix` = `numeric_df.cov()`.
- `preprocessing.py`: `impute_numeric_median(numeric_df) -> {imputed_df,
  dropped_columns, imputed_row_count}` (drop all-NaN columns first, then
  `fillna(median)`); `impute_numeric_knn(numeric_df, k)` same return shape using
  `sklearn.impute.KNNImputer`, with k clamped to `1..len-1`;
  `compare_imputations(numeric_df, median_df, knn_df)` returns a DataFrame
  indexed by original row with columns `column`, `median_fill`, `knn_fill`,
  `difference`, one row per originally-missing cell.
- `ml_processing.py`: `get_numeric_columns` (`select_dtypes("number")`);
  `_prepare_scoring_data(df, impute, impute_method, impute_k)` returns
  `(scoring_df or None, info)` and builds `imputation_comparison` whenever
  imputing and gaps exist; `detect_outliers_isolation_forest(df,
  contamination=0.05, impute=True, impute_method="median", impute_k=5)` uses
  `IsolationForest(contamination, random_state=42)`; `detect_outliers_knn(df,
  contamination, k=5, impute, impute_method, impute_k)` standardises features,
  takes the distance to the k-th neighbour (ask for k+1 because each row is its
  own neighbour), flags scores above `quantile(1 - contamination)`;
  both return counts, `flagged` (original columns + score column +
  `why_flagged`), `scores`, `model_settings`, `imputation_comparison`;
  `compare_outlier_methods(df, if_result, knn_result)` returns counts, agreement
  (both / union), Spearman rank correlation of the two score series, and a
  `consensus` table with `flagged_by` in {both, IF only, KNN only}.
- `app.py`: Flask, `static_folder="static", static_url_path=""`,
  `MAX_CONTENT_LENGTH = 1 GiB`, routes `/`, `/api/health`, `/api/analyze` as in
  section 5; `df_to_table` turns a DataFrame into `{columns, rows}` with
  NaN/inf -> null and numpy scalars -> Python.
- `cli.py`: prints sections in this order: dataset overview, numeric statistics,
  covariance, imputation comparison (only when imputing and gaps exist),
  Isolation Forest, KNN, comparison.

## Appendix A. Full source of every code file

Each file is under `### FILE: path` inside a five-backtick fence, exactly as
it is on disk. `static/samples/*.csv` are copies of the root sample CSVs.

### FILE: requirements.txt

`````text
pandas
numpy
scikit-learn
tabulate
flask

`````

### FILE: .python-version

`````
3.12

`````

### FILE: .gitignore

`````
__pycache__/
*.pyc
*.pyo
.venv/
venv/
.vercel
.env
.DS_Store
*.log

`````

### FILE: vercel.json

`````json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "functions": {
    "app.py": {
      "excludeFiles": "{__pycache__/**,**/__pycache__/**,*.pyc,.git/**,.claude/**,*.md}"
    }
  }
}

`````

### FILE: stats.py

`````python
"""Phase 1 descriptive statistics for the data profiling CLI."""

import pandas as pd


def dataset_overview(df: pd.DataFrame) -> dict:
    """Row/column counts plus per-column dtype and missing-value info."""
    columns_info = pd.DataFrame({
        "dtype": df.dtypes.astype(str),
        "missing": df.isna().sum(),
    })
    return {
        "rows": len(df),
        "columns": df.shape[1],
        "columns_info": columns_info,
    }


def numeric_summary(numeric_df: pd.DataFrame) -> pd.DataFrame:
    """Mean, median, mode, variance, std dev, kurtosis per numeric column."""
    rows = {}
    for col in numeric_df.columns:
        series = numeric_df[col].dropna()
        mode = series.mode()
        rows[col] = {
            "mean": series.mean(),
            "median": series.median(),
            "mode": mode.iloc[0] if not mode.empty else float("nan"),
            "variance": series.var(),
            "std_dev": series.std(),
            "kurtosis": series.kurt(),
        }
    return pd.DataFrame(rows).T


def five_point_summary(numeric_df: pd.DataFrame) -> pd.DataFrame:
    """Min, Q1, median, Q3, max per numeric column."""
    rows = {}
    for col in numeric_df.columns:
        series = numeric_df[col].dropna()
        rows[col] = {
            "min": series.min(),
            "Q1": series.quantile(0.25),
            "median": series.median(),
            "Q3": series.quantile(0.75),
            "max": series.max(),
        }
    return pd.DataFrame(rows).T


def covariance_matrix(numeric_df: pd.DataFrame) -> pd.DataFrame:
    return numeric_df.cov()

`````

### FILE: preprocessing.py

`````python
"""Preprocessing used ahead of outlier scoring (Isolation Forest and KNN):
median imputation and KNN imputation, plus a way to compare the two."""

import pandas as pd
from sklearn.impute import KNNImputer


def impute_numeric_median(numeric_df: pd.DataFrame) -> dict:
    """Fill missing values in each numeric column with that column's median.

    Columns that are entirely missing have no median to impute with, so they
    are dropped from the returned frame rather than left as NaN.
    """
    numeric_df = numeric_df.copy()
    fully_missing = numeric_df.columns[numeric_df.isna().all()]
    if len(fully_missing) > 0:
        numeric_df = numeric_df.drop(columns=fully_missing)

    imputed_mask = numeric_df.isna()
    imputed_df = numeric_df.fillna(numeric_df.median())

    return {
        "imputed_df": imputed_df,
        "dropped_columns": list(fully_missing),
        "imputed_row_count": int(imputed_mask.any(axis=1).sum()),
    }


def impute_numeric_knn(numeric_df: pd.DataFrame, k: int = 5) -> dict:
    """Fill missing values using K-Nearest Neighbors imputation.

    Each missing value is filled with the (uniformly weighted) average of
    that column's value across the k rows most similar to it, using
    whichever other numeric columns both rows actually have. This can pick
    up relationships between columns that a flat per-column median ignores -
    e.g. filling in income based on rows with a similar age and tenure,
    rather than just "the median income across everyone."

    Columns that are entirely missing have no signal to compute a distance
    from, so they are dropped first, same as impute_numeric_median.
    """
    numeric_df = numeric_df.copy()
    fully_missing = numeric_df.columns[numeric_df.isna().all()]
    if len(fully_missing) > 0:
        numeric_df = numeric_df.drop(columns=fully_missing)

    if numeric_df.shape[1] == 0 or len(numeric_df) == 0:
        return {"imputed_df": numeric_df, "dropped_columns": list(fully_missing), "imputed_row_count": 0}

    imputed_mask = numeric_df.isna()
    k = max(1, min(k, len(numeric_df) - 1)) if len(numeric_df) > 1 else 1
    values = KNNImputer(n_neighbors=k).fit_transform(numeric_df)
    imputed_df = pd.DataFrame(values, columns=numeric_df.columns, index=numeric_df.index)

    return {
        "imputed_df": imputed_df,
        "dropped_columns": list(fully_missing),
        "imputed_row_count": int(imputed_mask.any(axis=1).sum()),
    }


def compare_imputations(numeric_df: pd.DataFrame, median_df: pd.DataFrame, knn_df: pd.DataFrame) -> pd.DataFrame:
    """For every originally-missing cell, show the median fill next to the KNN fill.

    Only compares columns both imputations actually produced a value for
    (a column entirely missing might have been dropped by one or both).
    """
    mask = numeric_df.isna()
    common_cols = [c for c in numeric_df.columns if c in median_df.columns and c in knn_df.columns]

    rows = []
    for col in common_cols:
        for idx in numeric_df.index[mask[col]]:
            median_val = float(median_df.loc[idx, col])
            knn_val = float(knn_df.loc[idx, col])
            rows.append({
                "row": idx,
                "column": col,
                "median_fill": median_val,
                "knn_fill": knn_val,
                "difference": knn_val - median_val,
            })

    if not rows:
        return pd.DataFrame(columns=["row", "column", "median_fill", "knn_fill", "difference"]).set_index("row")

    return pd.DataFrame(rows).set_index("row")

`````

### FILE: ml_processing.py

`````python
"""Phase 2 ML integration: Isolation Forest and KNN multivariate outlier detection."""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

from preprocessing import compare_imputations, impute_numeric_knn, impute_numeric_median


def get_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df.select_dtypes(include="number")


def _explain_row(scoring_df: pd.DataFrame, means: pd.Series, stds: pd.Series, row_index, top_n: int = 2) -> str:
    """Describe which column(s) pushed a row's anomaly score, in plain terms.

    Neither Isolation Forest nor KNN gives per-feature reasoning, so this
    approximates one: the columns where the row sits furthest (in standard
    deviations) from that column's own average are the most likely drivers.
    """
    row = scoring_df.loc[row_index]
    z_scores = ((row - means) / stds).dropna()
    if z_scores.empty:
        return "n/a"
    top = z_scores.abs().sort_values(ascending=False).head(top_n).index
    parts = []
    for col in top:
        z = z_scores[col]
        direction = "above" if z > 0 else "below"
        parts.append(f"{col} ({abs(z):.1f} SD {direction} avg)")
    return ", ".join(parts)


def _empty_result(total_rows: int, impute: bool, dropped_columns: list = None) -> dict:
    return {
        "total_rows": total_rows,
        "scored_rows": 0,
        "skipped_rows": total_rows,
        "imputed": impute,
        "impute_method": None,
        "imputed_row_count": 0,
        "dropped_columns": dropped_columns or [],
        "imputation_comparison": pd.DataFrame(),
        "flagged_count": 0,
        "flagged": pd.DataFrame(),
        "scores": pd.Series(dtype=float),
        "model_settings": None,
    }


def _prepare_scoring_data(df: pd.DataFrame, impute: bool, impute_method: str = "median", impute_k: int = 5):
    """Build the complete numeric matrix both detectors score.

    When impute=True, both median and KNN imputation are computed regardless
    of impute_method - the one that's not used for scoring still feeds the
    imputation_comparison table, so you can see what each method would have
    filled in for every originally-missing cell.

    Returns (scoring_df, info). scoring_df is None when there is nothing to
    score, in which case info is a ready-made empty result.
    """
    numeric_df = get_numeric_columns(df)
    total_rows = len(df)

    if numeric_df.shape[1] == 0:
        return None, _empty_result(total_rows, impute)

    dropped_columns = []
    imputed_row_count = 0
    imputation_comparison = pd.DataFrame()

    if impute:
        median_imputation = impute_numeric_median(numeric_df)
        knn_imputation = impute_numeric_knn(numeric_df, k=impute_k)
        chosen = knn_imputation if impute_method == "knn" else median_imputation

        scoring_df = chosen["imputed_df"]
        dropped_columns = chosen["dropped_columns"]
        imputed_row_count = chosen["imputed_row_count"]

        if numeric_df.isna().any().any():
            imputation_comparison = compare_imputations(
                numeric_df, median_imputation["imputed_df"], knn_imputation["imputed_df"]
            )
    else:
        scoring_df = numeric_df.dropna()

    if scoring_df.shape[1] == 0 or len(scoring_df) == 0:
        return None, _empty_result(total_rows, impute, dropped_columns)

    scored_rows = len(scoring_df)
    return scoring_df, {
        "total_rows": total_rows,
        "scored_rows": scored_rows,
        "skipped_rows": total_rows - scored_rows,
        "imputed": impute,
        "impute_method": impute_method if impute else None,
        "imputed_row_count": imputed_row_count,
        "dropped_columns": dropped_columns,
        "imputation_comparison": imputation_comparison,
    }


def _finish_result(df, scoring_df, info, flagged_mask, scores, score_column, ascending, model_settings) -> dict:
    """Attach scores and explanations to the flagged rows and package the result."""
    flagged = df.loc[scoring_df.index[flagged_mask]].copy()
    flagged[score_column] = scores[flagged_mask]

    means = scoring_df.mean()
    stds = scoring_df.std().replace(0, pd.NA)
    flagged["why_flagged"] = [
        _explain_row(scoring_df, means, stds, idx) for idx in flagged.index
    ]
    flagged = flagged.sort_values(score_column, ascending=ascending)

    return {
        **info,
        "flagged_count": int(flagged_mask.sum()),
        "flagged": flagged,
        "scores": pd.Series(scores, index=scoring_df.index),
        "model_settings": model_settings,
    }


def detect_outliers_isolation_forest(
    df: pd.DataFrame, contamination: float = 0.05, impute: bool = True,
    impute_method: str = "median", impute_k: int = 5,
) -> dict:
    """Run Isolation Forest on the numeric columns of df.

    By default, missing numeric values are filled per-column with the median
    (see preprocessing.impute_numeric_median) so every row can be scored.
    Pass impute_method="knn" to fill with K-Nearest Neighbors imputation
    instead (preprocessing.impute_numeric_knn, using impute_k neighbours).
    Either way, the result's imputation_comparison table shows what both
    methods would have filled in for every originally-missing cell. Columns
    that are entirely missing can't be imputed and are excluded from
    scoring. Pass impute=False to instead drop any row with a missing numeric
    value (old behavior) and report it as skipped.

    Returns counts plus the flagged rows (original columns + anomaly_score
    and why_flagged), sorted from most to least anomalous.
    """
    scoring_df, info = _prepare_scoring_data(df, impute, impute_method, impute_k)
    if scoring_df is None:
        return info

    model = IsolationForest(contamination=contamination, random_state=42)
    predictions = model.fit_predict(scoring_df)
    scores = model.score_samples(scoring_df)

    return _finish_result(
        df, scoring_df, info,
        flagged_mask=predictions == -1,
        scores=scores,
        score_column="anomaly_score",
        ascending=True,
        model_settings={
            "method": "isolation_forest",
            "n_estimators": model.n_estimators,
            "contamination": contamination,
            "score_threshold": float(model.offset_),
        },
    )


def detect_outliers_knn(
    df: pd.DataFrame, contamination: float = 0.05, k: int = 5, impute: bool = True,
    impute_method: str = "median", impute_k: int = 5,
) -> dict:
    """Flag outliers by distance to the k-th nearest neighbour.

    A row's score is its distance to its k-th nearest neighbour: rows in sparse
    regions sit far from their neighbours and score high. The top
    `contamination` fraction of scores is flagged. Distances are only
    meaningful when every column is on the same scale, so features are
    standardised first (unlike Isolation Forest, which does not need this).
    Missing-value handling is identical to detect_outliers_isolation_forest,
    including the impute_method/impute_k options - note impute_k here is the
    KNN *imputer's* neighbour count, independent of k, the outlier-detection
    neighbour count.

    Returns counts plus the flagged rows (original columns + knn_distance and
    why_flagged), sorted from most to least anomalous.
    """
    scoring_df, info = _prepare_scoring_data(df, impute, impute_method, impute_k)
    if scoring_df is None:
        return info

    scored_rows = info["scored_rows"]
    if scored_rows < 2:
        return {
            **info,
            "flagged_count": 0,
            "flagged": pd.DataFrame(),
            "scores": pd.Series(dtype=float),
            "model_settings": None,
        }

    k = max(1, min(k, scored_rows - 1))
    X = StandardScaler().fit_transform(scoring_df)

    # each row is its own nearest neighbour (distance 0), so ask for k + 1
    distances, _ = NearestNeighbors(n_neighbors=k + 1).fit(X).kneighbors(X)
    scores = distances[:, k]

    threshold = float(np.quantile(scores, 1 - contamination))

    return _finish_result(
        df, scoring_df, info,
        flagged_mask=scores > threshold,
        scores=scores,
        score_column="knn_distance",
        ascending=False,
        model_settings={
            "method": "knn",
            "k": k,
            "contamination": contamination,
            "score_threshold": threshold,
        },
    )


def compare_outlier_methods(df: pd.DataFrame, if_result: dict, knn_result: dict) -> dict:
    """Compare what the two detectors flagged.

    Rows flagged by both methods are the high-confidence outliers; rows flagged
    by only one are worth a closer look but are less certain.
    """
    if_idx = set(if_result["flagged"].index)
    knn_idx = set(knn_result["flagged"].index)
    both = if_idx & knn_idx
    union = if_idx | knn_idx

    shared = if_result["scores"].index.intersection(knn_result["scores"].index)
    rank_correlation = float("nan")
    if len(shared) >= 3:
        # isolation forest: lower = more anomalous; knn: higher = more anomalous
        rank_correlation = float(
            (-if_result["scores"].loc[shared]).corr(knn_result["scores"].loc[shared], method="spearman")
        )

    consensus = pd.DataFrame()
    if union:
        order = {"both": 0, "IF only": 1, "KNN only": 1}
        consensus = df.loc[sorted(union)].copy()
        consensus["flagged_by"] = [
            "both" if i in both else ("IF only" if i in if_idx else "KNN only")
            for i in consensus.index
        ]
        consensus["anomaly_score"] = if_result["scores"].reindex(consensus.index)
        consensus["knn_distance"] = knn_result["scores"].reindex(consensus.index)
        explanations = [
            r["flagged"]["why_flagged"] if "why_flagged" in r["flagged"].columns else pd.Series(dtype=object)
            for r in (if_result, knn_result)
        ]
        consensus["why_flagged"] = (
            explanations[0].reindex(consensus.index).combine_first(explanations[1].reindex(consensus.index))
        )
        consensus["_rank"] = consensus["flagged_by"].map(order)
        consensus = consensus.sort_values(["_rank", "knn_distance"], ascending=[True, False]).drop(columns="_rank")

    return {
        "isolation_forest_count": len(if_idx),
        "knn_count": len(knn_idx),
        "both_count": len(both),
        "union_count": len(union),
        "agreement": len(both) / len(union) if union else float("nan"),
        "rank_correlation": rank_correlation,
        "consensus": consensus,
    }

`````

### FILE: cli.py

`````python
"""Entry point: reads a CSV and prints a full statistical + outlier profile."""

import argparse
import sys

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

from stats import covariance_matrix, dataset_overview, five_point_summary, numeric_summary
from ml_processing import (
    compare_outlier_methods,
    detect_outliers_isolation_forest,
    detect_outliers_knn,
    get_numeric_columns,
)

try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False


def print_table(df: pd.DataFrame, title: str = None) -> None:
    if title:
        print(f"\n{title}")
        print("-" * len(title))
    if df is None or df.empty:
        print("(none)")
        return
    if HAS_TABULATE:
        print(tabulate(df, headers="keys", tablefmt="psql", showindex=True))
    else:
        print(df.to_string())


def print_section(title: str) -> None:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def load_csv(path: str) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except FileNotFoundError:
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(1)
    except pd.errors.EmptyDataError:
        print(f"Error: file is empty: {path}", file=sys.stderr)
        sys.exit(1)
    except pd.errors.ParserError as e:
        print(f"Error: could not parse CSV: {e}", file=sys.stderr)
        sys.exit(1)


def describe_model(settings: dict) -> str:
    if settings["method"] == "knn":
        return (
            f"KNN (k={settings['k']}) - distance to the k-th nearest neighbour, on standardised features. "
            f"Rows with a distance above {settings['score_threshold']:.4f} are flagged as outliers."
        )
    return (
        f"IsolationForest with {settings['n_estimators']} trees. "
        f"Rows scoring below {settings['score_threshold']:.4f} are flagged as outliers."
    )


def print_detector_report(result: dict, contamination: float) -> None:
    print(f"Contamination: {contamination}")
    if result["model_settings"]:
        print(f"Model: {describe_model(result['model_settings'])}")
    if result["dropped_columns"]:
        print(
            "Excluded column(s) with no numeric data at all (nothing to "
            f"impute from): {', '.join(result['dropped_columns'])}"
        )
    print(f"Scored {result['scored_rows']} of {result['total_rows']} rows.")
    if result["imputed"]:
        if result["imputed_row_count"] > 0:
            method_label = "each column's median" if result["impute_method"] == "median" else "KNN imputation"
            print(
                f"Filled missing numeric values in {result['imputed_row_count']} "
                f"row(s) using {method_label} before scoring "
                "(use --no-impute to disable and skip those rows instead)."
            )
    elif result["skipped_rows"] > 0:
        print(
            f"Skipped {result['skipped_rows']} row(s) with missing values in "
            "numeric columns (these models can't score incomplete rows). "
            "Drop --no-impute to fill them with the column median instead."
        )
    print(f"\nFlagged {result['flagged_count']} outlier row(s):")
    print_table(result["flagged"])


def print_imputation_comparison(comparison_df: pd.DataFrame, impute_method: str) -> None:
    print(f"Active imputation method for scoring: {impute_method}")
    other = "KNN" if impute_method == "median" else "median"
    print(
        f"{len(comparison_df)} originally-missing cell(s) - what {impute_method} filled in "
        f"vs what {other} would have filled in instead:"
    )
    print_table(comparison_df)


def print_comparison(comparison: dict) -> None:
    print(
        f"Isolation Forest flagged {comparison['isolation_forest_count']} row(s); "
        f"KNN flagged {comparison['knn_count']} row(s)."
    )
    print(
        f"Both agree on {comparison['both_count']} row(s) - the high-confidence outliers "
        f"({comparison['union_count']} distinct rows flagged in total)."
    )
    if comparison["union_count"]:
        print(f"Agreement (flagged by both / flagged by either): {comparison['agreement']:.0%}")
    if comparison["rank_correlation"] == comparison["rank_correlation"]:
        print(
            "Rank correlation of the two methods' scores across all rows "
            f"(Spearman): {comparison['rank_correlation']:.3f}"
        )
    print("\nRows flagged by both methods are listed first; 'IF only' / 'KNN only' rows deserve a closer look.")
    print_table(comparison["consensus"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Data health & profiling CLI")
    parser.add_argument("csv_path", help="Path to the CSV file to profile")
    parser.add_argument(
        "--method",
        choices=["isolation_forest", "knn", "both"],
        default="both",
        help="Outlier detection method to run (default: both, followed by a comparison)",
    )
    parser.add_argument(
        "--contamination",
        type=float,
        default=0.05,
        help="Expected proportion of outliers, used by both methods (default: 0.05)",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=5,
        help="Number of neighbours for the KNN method (default: 5)",
    )
    parser.add_argument(
        "--no-impute",
        dest="impute",
        action="store_false",
        default=True,
        help=(
            "Disable imputation before scoring; rows "
            "with missing numeric values are skipped instead (old behavior)."
        ),
    )
    parser.add_argument(
        "--impute-method",
        choices=["median", "knn"],
        default="median",
        help="How to fill missing numeric values before scoring (default: median).",
    )
    parser.add_argument(
        "--impute-k",
        type=int,
        default=5,
        help="Neighbours used by KNN imputation (default: 5; only relevant with --impute-method knn).",
    )
    args = parser.parse_args()

    if not 0 < args.contamination <= 0.5:
        parser.error("--contamination must be greater than 0 and at most 0.5")
    if args.k < 1:
        parser.error("--k must be at least 1")
    if args.impute_k < 1:
        parser.error("--impute-k must be at least 1")

    df = load_csv(args.csv_path)
    if df.empty:
        print("The CSV has no rows to profile.")
        sys.exit(0)

    numeric_df = get_numeric_columns(df)

    print_section("DATASET OVERVIEW")
    overview = dataset_overview(df)
    print(f"Rows: {overview['rows']}")
    print(f"Columns: {overview['columns']}")
    print_table(overview["columns_info"], "Column dtypes & missing values")

    if numeric_df.shape[1] == 0:
        print("\nNo numeric columns found - skipping numeric statistics.")
    else:
        print_section("NUMERIC COLUMN STATISTICS")
        print_table(numeric_summary(numeric_df), "Central tendency, spread & kurtosis")
        print_table(five_point_summary(numeric_df), "Five-point summary")

        print_section("COVARIANCE MATRIX")
        print_table(covariance_matrix(numeric_df))

    if numeric_df.shape[1] == 0:
        print_section("OUTLIER DETECTION")
        print("No numeric columns available - skipping outlier detection.")
        return

    if_result = knn_result = None

    if args.method in ("isolation_forest", "both"):
        if_result = detect_outliers_isolation_forest(
            df, contamination=args.contamination, impute=args.impute,
            impute_method=args.impute_method, impute_k=args.impute_k,
        )

    if args.method in ("knn", "both"):
        knn_result = detect_outliers_knn(
            df, contamination=args.contamination, k=args.k, impute=args.impute,
            impute_method=args.impute_method, impute_k=args.impute_k,
        )

    comparison_source = if_result or knn_result
    if args.impute and comparison_source is not None and not comparison_source["imputation_comparison"].empty:
        print_section("IMPUTATION COMPARISON - MEDIAN vs KNN")
        print_imputation_comparison(comparison_source["imputation_comparison"], args.impute_method)

    if if_result is not None:
        print_section("ISOLATION FOREST - MULTIVARIATE OUTLIER DETECTION")
        print_detector_report(if_result, args.contamination)

    if knn_result is not None:
        print_section("KNN - DISTANCE-BASED OUTLIER DETECTION")
        print_detector_report(knn_result, args.contamination)

    if if_result is not None and knn_result is not None:
        print_section("COMPARISON - ISOLATION FOREST vs KNN")
        print_comparison(compare_outlier_methods(df, if_result, knn_result))


if __name__ == "__main__":
    main()

`````

### FILE: app.py

`````python
"""Web UI backend: a thin Flask wrapper around the existing CLI modules.

This intentionally reuses stats.py, preprocessing.py, and ml_processing.py
unchanged, so the web results match `python cli.py` exactly - no logic is
duplicated or re-implemented for the browser.
"""

import io
import math

import numpy as np
import pandas as pd
from flask import Flask, jsonify, request
from werkzeug.exceptions import RequestEntityTooLarge

from stats import covariance_matrix, dataset_overview, five_point_summary, numeric_summary
from ml_processing import (
    compare_outlier_methods,
    detect_outliers_isolation_forest,
    detect_outliers_knn,
    get_numeric_columns,
)

app = Flask(__name__, static_folder="static", static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024 * 1024  # 1 GB upload cap

MAX_CHART_ROWS = 3000  # cap raw points sent for client-side charting


def _clean(value):
    """Make a single value JSON-safe: NaN/inf -> None, numpy scalars -> plain Python."""
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        value = float(value)
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def df_to_table(df: pd.DataFrame) -> dict:
    """Turn a DataFrame into {columns, rows} the frontend can render as a table."""
    if df is None or df.empty:
        return {"columns": [] if df is None else [str(c) for c in df.columns], "rows": []}
    rows = []
    for idx, row in df.iterrows():
        record = {"_index": _clean(idx)}
        for col, val in row.items():
            record[str(col)] = _clean(val)
        rows.append(record)
    return {"columns": [str(c) for c in df.columns], "rows": rows}


def detector_payload(result: dict) -> dict:
    return {
        "total_rows": result["total_rows"],
        "scored_rows": result["scored_rows"],
        "skipped_rows": result["skipped_rows"],
        "imputed": result["imputed"],
        "impute_method": result["impute_method"],
        "imputed_row_count": result["imputed_row_count"],
        "dropped_columns": result["dropped_columns"],
        "flagged_count": result["flagged_count"],
        "flagged": df_to_table(result["flagged"]),
        "model_settings": result["model_settings"],
    }


@app.errorhandler(RequestEntityTooLarge)
def too_large(_e):
    return jsonify({"error": "File is too large. This demo accepts CSVs up to 1 GB."}), 413


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/api/analyze")
def analyze():
    file = request.files.get("file")
    if file is None or file.filename == "":
        return jsonify({"error": "No file uploaded. Attach a CSV as 'file'."}), 400

    method = request.form.get("method", "both")
    if method not in ("isolation_forest", "knn", "both"):
        return jsonify({"error": "method must be isolation_forest, knn, or both."}), 400

    try:
        contamination = float(request.form.get("contamination", 0.05))
    except ValueError:
        return jsonify({"error": "contamination must be a number."}), 400
    if not (0 < contamination <= 0.5):
        return jsonify({"error": "contamination must be greater than 0 and at most 0.5."}), 400

    try:
        k = int(request.form.get("k", 5))
    except ValueError:
        return jsonify({"error": "k must be an integer."}), 400
    if k < 1:
        return jsonify({"error": "k must be at least 1."}), 400

    impute = request.form.get("impute", "true").lower() != "false"

    impute_method = request.form.get("impute_method", "median")
    if impute_method not in ("median", "knn"):
        return jsonify({"error": "impute_method must be median or knn."}), 400

    try:
        impute_k = int(request.form.get("impute_k", 5))
    except ValueError:
        return jsonify({"error": "impute_k must be an integer."}), 400
    if impute_k < 1:
        return jsonify({"error": "impute_k must be at least 1."}), 400

    try:
        df = pd.read_csv(io.BytesIO(file.read()))
    except pd.errors.EmptyDataError:
        return jsonify({"error": "The uploaded file is empty."}), 400
    except pd.errors.ParserError as e:
        return jsonify({"error": f"Could not parse CSV: {e}"}), 400
    except UnicodeDecodeError:
        return jsonify({"error": "Could not decode file - is it a valid CSV (UTF-8)?"}), 400

    if df.empty:
        return jsonify({"error": "The CSV has no rows to profile."}), 400

    numeric_df = get_numeric_columns(df)
    overview = dataset_overview(df)

    response = {
        "rows": overview["rows"],
        "columns": overview["columns"],
        "columns_info": df_to_table(overview["columns_info"]),
        "has_numeric": numeric_df.shape[1] > 0,
    }

    if numeric_df.shape[1] > 0:
        response["numeric_summary"] = df_to_table(numeric_summary(numeric_df))
        response["five_point_summary"] = df_to_table(five_point_summary(numeric_df))
        response["covariance_matrix"] = df_to_table(covariance_matrix(numeric_df))

        # Raw (un-imputed) numeric columns, for client-side scatter plots / histograms.
        # Capped so a large upload can't blow up the response payload.
        response["raw_numeric"] = df_to_table(numeric_df.head(MAX_CHART_ROWS))
        response["raw_numeric_truncated"] = len(numeric_df) > MAX_CHART_ROWS

        results = {}
        if method in ("isolation_forest", "both"):
            results["isolation_forest"] = detect_outliers_isolation_forest(
                df, contamination=contamination, impute=impute,
                impute_method=impute_method, impute_k=impute_k,
            )
        if method in ("knn", "both"):
            results["knn"] = detect_outliers_knn(
                df, contamination=contamination, k=k, impute=impute,
                impute_method=impute_method, impute_k=impute_k,
            )

        response["results"] = {name: detector_payload(res) for name, res in results.items()}

        comparison_source = next(iter(results.values()))
        if impute and not comparison_source["imputation_comparison"].empty:
            response["imputation_comparison"] = {
                "active_method": impute_method,
                "table": df_to_table(comparison_source["imputation_comparison"]),
            }

        # index -> "both" | "isolation_forest" | "knn", for coloring chart points
        flagged_index_sets = {name: {str(i) for i in res["flagged"].index} for name, res in results.items()}
        flagged_by = {}
        if len(flagged_index_sets) == 2:
            if_idx, knn_idx = flagged_index_sets["isolation_forest"], flagged_index_sets["knn"]
            for key in if_idx & knn_idx:
                flagged_by[key] = "both"
            for key in if_idx - knn_idx:
                flagged_by[key] = "isolation_forest"
            for key in knn_idx - if_idx:
                flagged_by[key] = "knn"
        else:
            ((name, idx_set),) = flagged_index_sets.items()
            flagged_by = {key: name for key in idx_set}
        response["flagged_by"] = flagged_by

        if "isolation_forest" in results and "knn" in results:
            comparison = compare_outlier_methods(df, results["isolation_forest"], results["knn"])
            response["comparison"] = {
                "isolation_forest_count": comparison["isolation_forest_count"],
                "knn_count": comparison["knn_count"],
                "both_count": comparison["both_count"],
                "union_count": comparison["union_count"],
                "agreement": _clean(comparison["agreement"]),
                "rank_correlation": _clean(comparison["rank_correlation"]),
                "consensus": df_to_table(comparison["consensus"]),
            }

    return jsonify(response)


@app.get("/")
def index():
    return app.send_static_file("index.html")


if __name__ == "__main__":
    app.run(debug=True, port=5000)

`````

### FILE: static/index.html

`````html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Automated Data Health &amp; Profiling Dashboard</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' rx='20' fill='%23028090'/%3E%3Ctext x='50' y='68' font-size='58' text-anchor='middle' fill='white' font-family='Arial'%3E%E2%9C%93%3C/text%3E%3C/svg%3E" />
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />
<link rel="stylesheet" href="/style.css" />
</head>
<body>
<header class="topbar">
  <div class="topbar-inner">
    <div class="topbar-text">
      <h1>Automated Data Health &amp; Profiling Dashboard</h1>
      <p class="tagline">Upload a CSV, get statistics, and find unusual rows with Isolation Forest and KNN.</p>
    </div>
    <button type="button" id="theme-toggle" class="theme-toggle" title="Toggle dark mode" aria-label="Toggle dark mode">
      <span class="icon-sun">&#9728;</span><span class="icon-moon">&#9789;</span>
    </button>
  </div>
</header>

<main class="container">

  <section class="card" id="upload-card">
    <h2><span class="step-num">1</span>Choose a file</h2>
    <div class="upload-row">
      <label class="file-drop" for="file-input">
        <input type="file" id="file-input" accept=".csv" />
        <svg class="upload-icon" viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M12 16V4M12 4l-4 4M12 4l4 4"/><path d="M4 16v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3"/></svg>
        <span id="file-name">Click to choose a CSV, or drop one here</span>
      </label>
      <div class="samples">
        <span class="samples-label">or try a sample:</span>
        <button type="button" class="sample-btn" data-sample="sample_numeric.csv">Clean numeric (15 rows)</button>
        <button type="button" class="sample-btn" data-sample="sample_messy.csv">Messy / mixed types (16 rows)</button>
        <button type="button" class="sample-btn" data-sample="sample_200.csv">200 rows, 8 planted outliers</button>
      </div>
    </div>
  </section>

  <section class="card hidden" id="preview-card">
    <div class="section-head">
      <h2>Quick Preview</h2>
      <span class="note-line" id="preview-note"></span>
    </div>
    <p class="note-line">Box plot per numeric column, computed in your browser straight from the raw file - each has its own scale, so a column with a much larger range (like income) doesn't flatten the others.</p>
    <div class="chart-grid" id="preview-chart-grid"></div>
  </section>

  <section class="card" id="options-card">
    <h2><span class="step-num">2</span>Options</h2>
    <div class="options-grid">
      <label>
        Method
        <select id="opt-method">
          <option value="both" selected>Both (Isolation Forest + KNN)</option>
          <option value="isolation_forest">Isolation Forest only</option>
          <option value="knn">KNN only</option>
        </select>
      </label>
      <label>
        Contamination (expected outlier share)
        <input type="number" id="opt-contamination" min="0.01" max="0.5" step="0.01" value="0.05" />
      </label>
      <label id="k-field">
        k (KNN neighbours, for outlier detection)
        <input type="number" id="opt-k" min="1" step="1" value="5" />
      </label>
      <label class="checkbox-field">
        <input type="checkbox" id="opt-impute" checked />
        Fill missing values before scoring
      </label>
      <label id="impute-method-field">
        Fill missing values using
        <select id="opt-impute-method">
          <option value="median" selected>Median (per column)</option>
          <option value="knn">KNN imputation</option>
        </select>
      </label>
      <label id="impute-k-field" class="hidden">
        Neighbours for KNN imputation
        <input type="number" id="opt-impute-k" min="1" step="1" value="5" />
      </label>
    </div>
    <button type="button" id="analyze-btn" class="primary-btn">
      <span class="btn-label">Analyze</span>
      <span class="spinner hidden"></span>
    </button>
    <p class="hint">Runs entirely on the server for this request; nothing is stored. Max file size 1&nbsp;GB - very large files may take a long time to score.</p>
  </section>

  <section id="status-area"></section>

  <section id="results" class="results hidden"></section>

</main>

<footer class="footer">
  <p>Automated Data Health &amp; Profiling Dashboard - the same statistics and detection logic as the command-line tool (<code>cli.py</code>), reused unchanged in this web UI.</p>
</footer>

<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/@sgratzl/chartjs-chart-boxplot@4/build/index.umd.min.js"></script>
<script src="/app.js"></script>
</body>
</html>

`````

### FILE: static/style.css

`````css
:root {
  --navy: #1a1a2e;
  --navy-light: #16213e;
  --teal: #028090;
  --teal-light: #02c39a;
  --bg: #f5f6fa;
  --card-bg: #ffffff;
  --border: #e2e5ec;
  --text: #1c1e26;
  --muted: #5b6270;
  --danger: #b3261e;
  --danger-bg: #fdecea;
  --good-bg: #eaf7f0;
  --good-text: #0f6b3f;
  --thead-bg: #1a1a2e;
  --thead-text: #ffffff;
  --row-alt: #fafbfd;
  --shadow: 0 1px 2px rgba(20, 22, 40, 0.05), 0 1px 12px rgba(20, 22, 40, 0.04);
  --shadow-hover: 0 4px 18px rgba(20, 22, 40, 0.09);
  --code-bg: #eef1fb;
  --mono: "JetBrains Mono", "Courier New", monospace;
}

:root[data-theme="dark"] {
  --navy: #12131f;
  --navy-light: #0d0e17;
  --teal: #16b3c4;
  --teal-light: #2be0ac;
  --bg: #0f1016;
  --card-bg: #181a24;
  --border: #2a2c3a;
  --text: #e7e8ee;
  --muted: #9297ab;
  --danger: #ff6b62;
  --danger-bg: #3a1f20;
  --good-bg: #123829;
  --good-text: #5fe3a3;
  --thead-bg: #0d0e17;
  --thead-text: #eef1fb;
  --row-alt: #1c1e2b;
  --shadow: 0 1px 2px rgba(0, 0, 0, 0.3), 0 1px 12px rgba(0, 0, 0, 0.25);
  --shadow-hover: 0 4px 18px rgba(0, 0, 0, 0.4);
  --code-bg: #20233a;
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --navy: #12131f;
    --navy-light: #0d0e17;
    --teal: #16b3c4;
    --teal-light: #2be0ac;
    --bg: #0f1016;
    --card-bg: #181a24;
    --border: #2a2c3a;
    --text: #e7e8ee;
    --muted: #9297ab;
    --danger: #ff6b62;
    --danger-bg: #3a1f20;
    --good-bg: #123829;
    --good-text: #5fe3a3;
    --thead-bg: #0d0e17;
    --thead-text: #eef1fb;
    --row-alt: #1c1e2b;
    --shadow: 0 1px 2px rgba(0, 0, 0, 0.3), 0 1px 12px rgba(0, 0, 0, 0.25);
    --shadow-hover: 0 4px 18px rgba(0, 0, 0, 0.4);
    --code-bg: #20233a;
  }
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: "Inter", -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.55;
  transition: background 0.2s ease, color 0.2s ease;
}

.topbar {
  background: linear-gradient(135deg, var(--navy) 0%, var(--navy-light) 100%);
  color: #fff;
  padding: 30px 20px;
}

.topbar-inner {
  max-width: 1040px;
  margin: 0 auto;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
}

.topbar h1 {
  margin: 0 0 6px;
  font-size: 1.65rem;
  font-weight: 700;
  letter-spacing: -0.01em;
}

.tagline {
  margin: 0;
  color: #c7ccf0;
  font-size: 0.95rem;
}

.theme-toggle {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.25);
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
  cursor: pointer;
  font-size: 1.1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s, transform 0.15s;
}

.theme-toggle:hover {
  background: rgba(255, 255, 255, 0.18);
  transform: scale(1.06);
}

.icon-moon {
  display: none;
}

:root[data-theme="dark"] .icon-sun {
  display: none;
}

:root[data-theme="dark"] .icon-moon {
  display: inline;
}

.container {
  max-width: 1040px;
  margin: 26px auto;
  padding: 0 20px 40px;
}

.card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 22px 24px;
  margin-bottom: 20px;
  box-shadow: var(--shadow);
  animation: fadeIn 0.35s ease;
}

.card h2 {
  margin: 0 0 16px;
  font-size: 1.05rem;
  color: var(--text);
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 600;
}

.step-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--teal);
  color: #fff;
  font-size: 0.78rem;
  font-weight: 700;
  flex-shrink: 0;
}

.upload-row {
  display: flex;
  flex-wrap: wrap;
  gap: 18px;
  align-items: center;
}

.file-drop {
  flex: 1 1 320px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  min-height: 68px;
  border: 2px dashed var(--border);
  border-radius: 10px;
  cursor: pointer;
  padding: 14px;
  text-align: center;
  color: var(--muted);
  transition: border-color 0.15s, background 0.15s, transform 0.1s;
}

.file-drop:hover {
  border-color: var(--teal);
  background: var(--code-bg);
}

.file-drop.dragover {
  border-color: var(--teal);
  background: var(--code-bg);
  transform: scale(1.01);
}

.file-drop input[type="file"] {
  display: none;
}

.upload-icon {
  flex-shrink: 0;
  opacity: 0.7;
}

.samples {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.samples-label {
  font-size: 0.85rem;
  color: var(--muted);
  margin-right: 4px;
}

.sample-btn {
  background: var(--code-bg);
  border: 1px solid var(--border);
  color: var(--navy-light);
  border-radius: 6px;
  padding: 7px 12px;
  font-size: 0.82rem;
  cursor: pointer;
  transition: background 0.12s, transform 0.1s;
}

:root[data-theme="dark"] .sample-btn,
:root:not([data-theme="light"]) .sample-btn {
  color: var(--teal-light);
}

.sample-btn:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow);
}

.options-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  gap: 16px;
  margin-bottom: 18px;
}

.options-grid label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 0.85rem;
  color: var(--muted);
}

.options-grid input,
.options-grid select {
  padding: 9px 11px;
  border: 1px solid var(--border);
  border-radius: 7px;
  font-size: 0.95rem;
  color: var(--text);
  background: var(--card-bg);
  font-family: inherit;
  transition: border-color 0.12s, box-shadow 0.12s;
}

.options-grid input:focus,
.options-grid select:focus {
  outline: none;
  border-color: var(--teal);
  box-shadow: 0 0 0 3px rgba(2, 128, 144, 0.15);
}

.checkbox-field {
  flex-direction: row !important;
  align-items: center;
  gap: 8px !important;
}

.checkbox-field input {
  width: auto;
}

.primary-btn {
  background: var(--teal);
  color: #fff;
  border: none;
  padding: 11px 26px;
  border-radius: 8px;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  transition: background 0.15s, transform 0.1s;
}

.primary-btn:hover:not(:disabled) {
  background: #026f7d;
  transform: translateY(-1px);
}

.primary-btn:disabled {
  background: #9fb9bc;
  cursor: not-allowed;
  transform: none;
}

.spinner {
  width: 15px;
  height: 15px;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

.hint {
  margin: 10px 0 0;
  font-size: 0.8rem;
  color: var(--muted);
}

.small-btn {
  background: var(--code-bg);
  border: 1px solid var(--border);
  color: var(--text);
  border-radius: 6px;
  padding: 6px 12px;
  font-size: 0.78rem;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: background 0.12s;
}

.small-btn:hover {
  background: var(--border);
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 12px;
}

.section-head h2,
.section-head h3 {
  margin: 0;
}

#status-area {
  max-width: 1040px;
  margin: 0 auto 20px;
}

.status-box {
  border-radius: 8px;
  padding: 12px 16px;
  font-size: 0.9rem;
  animation: fadeIn 0.2s ease;
}

.status-error {
  background: var(--danger-bg);
  color: var(--danger);
  border: 1px solid var(--danger);
}

.status-loading {
  background: var(--code-bg);
  color: var(--navy-light);
  border: 1px solid var(--border);
}

:root[data-theme="dark"] .status-loading,
:root:not([data-theme="light"]) .status-loading {
  color: var(--teal-light);
}

.hidden {
  display: none !important;
}

.results h2 {
  font-size: 1.05rem;
  color: var(--text);
  font-weight: 600;
}

.results h3 {
  font-size: 0.95rem;
  color: var(--muted);
  margin: 4px 0 10px;
}

.model-line {
  background: var(--code-bg);
  border-radius: 6px;
  padding: 9px 13px;
  font-size: 0.85rem;
  color: var(--navy-light);
  margin-bottom: 12px;
  font-family: var(--mono);
}

:root[data-theme="dark"] .model-line,
:root:not([data-theme="light"]) .model-line {
  color: var(--teal-light);
}

.note-line {
  font-size: 0.85rem;
  color: var(--muted);
  margin-bottom: 10px;
}

.stat-row {
  display: flex;
  gap: 22px;
  flex-wrap: wrap;
  margin-bottom: 6px;
  font-size: 0.9rem;
}

.stat-row b {
  color: var(--text);
}

.stat-tiles {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.stat-tile {
  background: var(--code-bg);
  border-radius: 10px;
  padding: 14px 16px;
  text-align: center;
}

.stat-tile .tile-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--teal);
  display: block;
}

.stat-tile .tile-label {
  font-size: 0.75rem;
  color: var(--muted);
  margin-top: 2px;
  display: block;
}

.table-wrap {
  overflow-x: auto;
  margin-bottom: 18px;
  border: 1px solid var(--border);
  border-radius: 10px;
  max-height: 420px;
  overflow-y: auto;
}

table {
  border-collapse: collapse;
  width: 100%;
  font-size: 0.83rem;
  white-space: nowrap;
}

thead th {
  background: var(--thead-bg);
  color: var(--thead-text);
  text-align: left;
  padding: 9px 11px;
  position: sticky;
  top: 0;
  z-index: 1;
  user-select: none;
}

thead th.sortable {
  cursor: pointer;
}

thead th.sortable:hover {
  background: var(--teal);
}

thead th .sort-arrow {
  margin-left: 5px;
  opacity: 0.55;
  font-size: 0.7rem;
}

thead th.sort-active .sort-arrow {
  opacity: 1;
}

tbody td {
  padding: 7px 11px;
  border-bottom: 1px solid var(--border);
}

tbody tr:nth-child(even) {
  background: var(--row-alt);
}

tbody tr.flagged-both {
  background: #fff4e5;
}

:root[data-theme="dark"] tbody tr.flagged-both,
:root:not([data-theme="light"]) tbody tr.flagged-both {
  background: #3a2e12;
}

.badge {
  display: inline-block;
  padding: 2px 9px;
  border-radius: 999px;
  font-size: 0.73rem;
  font-weight: 600;
}

.badge-both {
  background: #ffe6b3;
  color: #7a4b00;
}

.badge-if {
  background: #dbe9ff;
  color: #1b4f8a;
}

.badge-knn {
  background: #dcf5e6;
  color: #146c3a;
}

.chart-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  margin-bottom: 14px;
  align-items: flex-end;
}

.chart-controls label {
  display: flex;
  flex-direction: column;
  gap: 5px;
  font-size: 0.8rem;
  color: var(--muted);
}

.chart-controls select {
  padding: 7px 9px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--card-bg);
  color: var(--text);
  font-family: inherit;
}

.chart-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 20px;
  margin-bottom: 8px;
}

.chart-box {
  background: var(--code-bg);
  border-radius: 10px;
  padding: 16px;
}

.chart-box h4 {
  margin: 0 0 10px;
  font-size: 0.88rem;
  color: var(--muted);
  font-weight: 600;
}

.chart-box canvas {
  max-height: 320px;
}

.truncation-note {
  font-size: 0.78rem;
  color: var(--muted);
  font-style: italic;
  margin-top: 6px;
}

.footer {
  text-align: center;
  color: var(--muted);
  font-size: 0.8rem;
  padding: 24px 20px;
}

.footer code {
  background: var(--code-bg);
  padding: 1px 6px;
  border-radius: 4px;
}

/* ---------- responsive ---------- */
@media (max-width: 640px) {
  .topbar {
    padding: 22px 16px;
  }
  .topbar h1 {
    font-size: 1.3rem;
  }
  .tagline {
    font-size: 0.85rem;
  }
  .container {
    padding: 0 14px 30px;
    margin: 18px auto;
  }
  .card {
    padding: 16px 16px;
  }
  .options-grid {
    grid-template-columns: 1fr;
  }
  .upload-row {
    flex-direction: column;
    align-items: stretch;
  }
  .samples {
    justify-content: flex-start;
  }
  .stat-row {
    flex-direction: column;
    gap: 8px;
  }
  table {
    font-size: 0.76rem;
  }
  .theme-toggle {
    width: 36px;
    height: 36px;
  }
}

`````

### FILE: static/app.js

`````javascript
// ---------------------------------------------------------------------------
// Theme
// ---------------------------------------------------------------------------
const themeToggle = document.getElementById("theme-toggle");
const savedTheme = localStorage.getItem("theme");
if (savedTheme) document.documentElement.setAttribute("data-theme", savedTheme);

themeToggle.addEventListener("click", () => {
  const current = document.documentElement.getAttribute("data-theme");
  const isDark = current
    ? current === "dark"
    : window.matchMedia("(prefers-color-scheme: dark)").matches;
  const next = isDark ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  localStorage.setItem("theme", next);
});

// ---------------------------------------------------------------------------
// File selection
// ---------------------------------------------------------------------------
const fileInput = document.getElementById("file-input");
const fileNameEl = document.getElementById("file-name");
const fileDrop = document.querySelector(".file-drop");
const analyzeBtn = document.getElementById("analyze-btn");
const methodSelect = document.getElementById("opt-method");
const kField = document.getElementById("k-field");
const imputeCheckbox = document.getElementById("opt-impute");
const imputeMethodSelect = document.getElementById("opt-impute-method");
const imputeMethodField = document.getElementById("impute-method-field");
const imputeKField = document.getElementById("impute-k-field");
const statusArea = document.getElementById("status-area");
const resultsEl = document.getElementById("results");

function syncImputeFields() {
  const on = imputeCheckbox.checked;
  imputeMethodField.classList.toggle("hidden", !on);
  imputeKField.classList.toggle("hidden", !(on && imputeMethodSelect.value === "knn"));
}
imputeCheckbox.addEventListener("change", syncImputeFields);
imputeMethodSelect.addEventListener("change", syncImputeFields);
syncImputeFields();

let currentFile = null;

function setFile(file) {
  currentFile = file;
  fileNameEl.textContent = file ? `${file.name} (${(file.size / 1024).toFixed(1)} KB)` : "Click to choose a CSV, or drop one here";
  if (file) updatePreview(file);
}

// ---------------------------------------------------------------------------
// Quick preview: parsed client-side the instant a file is chosen, before
// "Analyze" is ever clicked - no server round-trip.
// ---------------------------------------------------------------------------
const previewCard = document.getElementById("preview-card");
const previewNote = document.getElementById("preview-note");
const previewChartGrid = document.getElementById("preview-chart-grid");
let previewCharts = [];
let previewToken = 0;

function parseCsvText(text) {
  const rows = [];
  let row = [];
  let field = "";
  let inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"') {
        if (text[i + 1] === '"') { field += '"'; i++; } else { inQuotes = false; }
      } else {
        field += c;
      }
    } else if (c === '"') {
      inQuotes = true;
    } else if (c === ",") {
      row.push(field);
      field = "";
    } else if (c === "\n" || c === "\r") {
      if (c === "\r" && text[i + 1] === "\n") i++;
      row.push(field);
      field = "";
      if (row.length > 1 || row[0] !== "") rows.push(row);
      row = [];
    } else {
      field += c;
    }
  }
  if (field !== "" || row.length) {
    row.push(field);
    rows.push(row);
  }
  return rows;
}

// Matches pandas.read_csv's default na_values, so a column that mixes real
// numbers with these tokens is still recognized as numeric here - just like
// the Python backend (which is what actually scores the data).
const NA_TOKENS = new Set([
  "", "#N/A", "#N/A N/A", "#NA", "-1.#IND", "-1.#QNAN", "-NaN", "-nan",
  "1.#IND", "1.#QNAN", "<NA>", "N/A", "NA", "NULL", "NaN", "None", "n/a", "nan", "null",
]);

function extractNumericColumns(text) {
  const rows = parseCsvText(text);
  if (rows.length < 2) return {};
  const header = rows[0];
  const dataRows = rows.slice(1).filter((r) => r.length === header.length);
  const columns = {};
  header.forEach((name, ci) => {
    const cells = dataRows.map((r) => (r[ci] !== undefined ? r[ci].trim() : ""));
    const informative = cells.filter((v) => !NA_TOKENS.has(v));
    const allNumeric = informative.length > 0 && informative.every((v) => Number.isFinite(Number(v)));
    if (allNumeric) columns[name || `column_${ci}`] = informative.map(Number);
  });
  return columns;
}

function destroyPreviewCharts() {
  previewCharts.forEach((c) => c.destroy());
  previewCharts = [];
}

async function updatePreview(file) {
  const token = ++previewToken;
  try {
    const text = await file.text();
    if (token !== previewToken) return; // a newer file was chosen meanwhile
    const columns = extractNumericColumns(text);
    const names = Object.keys(columns);
    destroyPreviewCharts();
    previewCard.classList.remove("hidden");

    if (names.length === 0) {
      previewChartGrid.innerHTML = "";
      previewNote.textContent = "No numeric columns detected for a preview.";
      return;
    }

    previewNote.textContent = `${names.length} numeric column(s), computed from the raw file (client-side, quick estimate)`;
    previewChartGrid.innerHTML = names
      .map((n) => `<div class="chart-box"><h4>${n}</h4><canvas id="preview-box-${n.replace(/[^a-zA-Z0-9_-]/g, "_")}"></canvas></div>`)
      .join("");

    names.forEach((n) => {
      const canvas = document.getElementById(`preview-box-${n.replace(/[^a-zA-Z0-9_-]/g, "_")}`);
      previewCharts.push(
        new Chart(canvas, {
          type: "boxplot",
          data: {
            labels: [n],
            datasets: [
              {
                label: n,
                data: [columns[n]],
                backgroundColor: "rgba(2, 128, 144, 0.25)",
                borderColor: "#028090",
                borderWidth: 1.5,
                outlierColor: "#e8524d",
                itemRadius: 2,
              },
            ],
          },
          options: baseChartOptions({ plugins: { legend: { display: false } } }),
        })
      );
    });
  } catch (err) {
    if (token !== previewToken) return;
    previewCard.classList.remove("hidden");
    previewChartGrid.innerHTML = "";
    previewNote.textContent = "Could not preview this file (is it a valid CSV?).";
  }
}

fileInput.addEventListener("change", () => {
  if (fileInput.files.length) setFile(fileInput.files[0]);
});

["dragover", "dragleave", "drop"].forEach((evt) => {
  fileDrop.addEventListener(evt, (e) => {
    e.preventDefault();
    fileDrop.classList.toggle("dragover", evt === "dragover");
  });
});
fileDrop.addEventListener("drop", (e) => {
  const file = e.dataTransfer.files[0];
  if (file) setFile(file);
});

document.querySelectorAll(".sample-btn").forEach((btn) => {
  btn.addEventListener("click", async () => {
    const name = btn.dataset.sample;
    const resp = await fetch(`/samples/${name}`);
    const blob = await resp.blob();
    setFile(new File([blob], name, { type: "text/csv" }));
  });
});

methodSelect.addEventListener("change", () => {
  kField.style.display = methodSelect.value === "isolation_forest" ? "none" : "flex";
});

function showStatus(kind, message) {
  statusArea.innerHTML = message ? `<div class="status-box status-${kind}">${message}</div>` : "";
}

// ---------------------------------------------------------------------------
// Formatting helpers
// ---------------------------------------------------------------------------
function fmt(v) {
  if (v === null || v === undefined) return "";
  if (typeof v === "number") {
    if (Number.isInteger(v)) return String(v);
    return v.toFixed(Math.abs(v) < 1 ? 4 : 3);
  }
  return String(v);
}

function csvEscape(v) {
  const s = v === null || v === undefined ? "" : String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

function downloadCsv(filename, columns, rows, showIndex) {
  const header = (showIndex ? [""] : []).concat(columns);
  const lines = [header.map(csvEscape).join(",")];
  rows.forEach((row) => {
    const cells = (showIndex ? [row._index] : []).concat(columns.map((c) => row[c]));
    lines.push(cells.map(csvEscape).join(","));
  });
  const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

// ---------------------------------------------------------------------------
// Sortable, exportable tables
// ---------------------------------------------------------------------------
let tableSeq = 0;
const tableState = {};

function compareValues(a, b) {
  const an = a === null || a === undefined;
  const bn = b === null || b === undefined;
  if (an && bn) return 0;
  if (an) return 1;
  if (bn) return -1;
  if (typeof a === "number" && typeof b === "number") return a - b;
  return String(a).localeCompare(String(b), undefined, { numeric: true });
}

function renderTableCard(title, table, opts = {}) {
  const id = `tbl${tableSeq++}`;
  const showIndex = opts.showIndex !== false;
  tableState[id] = {
    columns: table && table.columns ? table.columns : [],
    rows: table && table.rows ? table.rows.slice() : [],
    showIndex,
    rowClass: opts.rowClass || null,
    filename: opts.filename || "table.csv",
    sortCol: null,
    sortDir: 1,
  };
  const head = title
    ? `<div class="section-head"><h3>${title}</h3><button type="button" class="small-btn" onclick="exportTable('${id}')">&#8681; Export CSV</button></div>`
    : "";
  return `${head}<div id="${id}"></div>`;
}

function drawTable(id) {
  const state = tableState[id];
  const container = document.getElementById(id);
  if (!state || !container) return;
  if (state.rows.length === 0) {
    container.innerHTML = `<p class="note-line">(none)</p>`;
    return;
  }
  const headCells =
    (state.showIndex ? "<th></th>" : "") +
    state.columns
      .map((c) => {
        const active = state.sortCol === c;
        const arrow = active ? (state.sortDir === 1 ? "&#9650;" : "&#9660;") : "&#8597;";
        return `<th class="sortable${active ? " sort-active" : ""}" onclick="sortTable('${id}','${c}')">${c}<span class="sort-arrow">${arrow}</span></th>`;
      })
      .join("");
  const body = state.rows
    .map((row) => {
      const cls = state.rowClass ? state.rowClass(row) : "";
      const idxCell = state.showIndex ? `<td>${fmt(row._index)}</td>` : "";
      const cells = state.columns.map((c) => `<td>${fmt(row[c])}</td>`).join("");
      return `<tr class="${cls}">${idxCell}${cells}</tr>`;
    })
    .join("");
  container.innerHTML = `<div class="table-wrap"><table><thead><tr>${headCells}</tr></thead><tbody>${body}</tbody></table></div>`;
}

window.sortTable = function (id, col) {
  const state = tableState[id];
  if (!state) return;
  state.sortDir = state.sortCol === col ? -state.sortDir : 1;
  state.sortCol = col;
  state.rows.sort((a, b) => state.sortDir * compareValues(a[col], b[col]));
  drawTable(id);
};

window.exportTable = function (id) {
  const state = tableState[id];
  if (!state) return;
  downloadCsv(state.filename, state.columns, state.rows, state.showIndex);
};

function drawAllTables() {
  Object.keys(tableState).forEach(drawTable);
}

// ---------------------------------------------------------------------------
// Charts
// ---------------------------------------------------------------------------
let activeCharts = [];

function destroyCharts() {
  activeCharts.forEach((c) => c.destroy());
  activeCharts = [];
}

const CHART_COLORS = {
  both: "#e8a33d",
  isolation_forest: "#3d7ce8",
  knn: "#2fbf71",
  none: "#9aa0b0",
};
const CHART_LABELS = { both: "Flagged by both", isolation_forest: "Isolation Forest only", knn: "KNN only", none: "Not flagged" };

function baseChartOptions(extra = {}) {
  const gridColor = getComputedStyle(document.documentElement).getPropertyValue("--border").trim();
  const textColor = getComputedStyle(document.documentElement).getPropertyValue("--muted").trim();
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { labels: { color: textColor } } },
    scales: {
      x: { grid: { color: gridColor }, ticks: { color: textColor } },
      y: { grid: { color: gridColor }, ticks: { color: textColor } },
    },
    ...extra,
  };
}

function buildScatterChart(canvas, raw, flaggedBy, xCol, yCol) {
  const buckets = { both: [], isolation_forest: [], knn: [], none: [] };
  raw.rows.forEach((row) => {
    const x = row[xCol];
    const y = row[yCol];
    if (x === null || y === null || x === undefined || y === undefined) return;
    const status = flaggedBy[String(row._index)] || "none";
    buckets[status].push({ x, y });
  });
  const datasets = Object.keys(buckets)
    .filter((k) => buckets[k].length)
    .map((k) => ({
      label: CHART_LABELS[k],
      data: buckets[k],
      backgroundColor: CHART_COLORS[k],
      pointRadius: k === "none" ? 3 : 5,
      pointHoverRadius: 7,
    }));
  return new Chart(canvas, {
    type: "scatter",
    data: { datasets },
    options: baseChartOptions({
      scales: {
        x: { title: { display: true, text: xCol, color: "#8890a4" } },
        y: { title: { display: true, text: yCol, color: "#8890a4" } },
      },
    }),
  });
}

function computeBins(values, binCount) {
  const min = Math.min(...values);
  const max = Math.max(...values);
  if (min === max) return { labels: [String(min)], counts: [values.length] };
  const width = (max - min) / binCount;
  const counts = new Array(binCount).fill(0);
  values.forEach((v) => {
    let idx = Math.floor((v - min) / width);
    if (idx >= binCount) idx = binCount - 1;
    counts[idx]++;
  });
  const labels = counts.map((_, i) => (min + i * width).toFixed(1));
  return { labels, counts };
}

function buildHistogram(canvas, raw, col) {
  const values = raw.rows.map((r) => r[col]).filter((v) => v !== null && v !== undefined);
  const { labels, counts } = computeBins(values, Math.min(20, Math.max(5, Math.round(Math.sqrt(values.length)))));
  return new Chart(canvas, {
    type: "bar",
    data: { labels, datasets: [{ label: col, data: counts, backgroundColor: "#028090" }] },
    options: baseChartOptions({ plugins: { legend: { display: false } } }),
  });
}

function buildScoreChart(canvas, method, result) {
  const scoreKey = method === "knn" ? "knn_distance" : "anomaly_score";
  const rows = result.flagged.rows.slice();
  const labels = rows.map((r) => `id ${r._index}`);
  const values = rows.map((r) => r[scoreKey]);
  const threshold = result.model_settings ? result.model_settings.score_threshold : null;
  const datasets = [
    {
      type: "bar",
      label: method === "knn" ? "KNN distance" : "Anomaly score",
      data: values,
      backgroundColor: method === "knn" ? CHART_COLORS.knn : CHART_COLORS.isolation_forest,
    },
  ];
  if (threshold !== null) {
    datasets.push({
      type: "line",
      label: "Threshold",
      data: labels.map(() => threshold),
      borderColor: "#e8524d",
      borderDash: [6, 4],
      pointRadius: 0,
      borderWidth: 2,
    });
  }
  return new Chart(canvas, {
    type: "bar",
    data: { labels, datasets },
    options: baseChartOptions({ indexAxis: "y" }),
  });
}

function renderVisualizations(data) {
  if (!data.raw_numeric || data.raw_numeric.rows.length === 0) return "";
  const numCols = data.raw_numeric.columns;
  if (numCols.length === 0) return "";

  const xOptions = numCols.map((c, i) => `<option value="${c}" ${i === 0 ? "selected" : ""}>${c}</option>`).join("");
  const yOptions = numCols.map((c, i) => `<option value="${c}" ${i === 1 ? "selected" : (numCols.length === 1 ? "selected" : "")}>${c}</option>`).join("");
  const histOptions = numCols.map((c, i) => `<option value="${c}" ${i === 0 ? "selected" : ""}>${c}</option>`).join("");

  const scoreCharts = data.results
    ? Object.keys(data.results)
        .filter((name) => data.results[name].flagged.rows.length > 0)
        .map(
          (name) =>
            `<div class="chart-box"><h4>${name === "knn" ? "KNN distance" : "Isolation Forest anomaly score"} (flagged rows)</h4><canvas id="chart-score-${name}"></canvas></div>`
        )
        .join("")
    : "";

  const truncNote = data.raw_numeric_truncated
    ? `<p class="truncation-note">Showing the first ${data.raw_numeric.rows.length} rows in charts (file has more rows than the chart limit).</p>`
    : "";

  return `
    <div class="card">
      <h2>Visualizations</h2>
      ${truncNote}
      <div class="chart-controls">
        <label>X axis <select id="scatter-x">${xOptions}</select></label>
        <label>Y axis <select id="scatter-y">${yOptions}</select></label>
        <label>Histogram column <select id="hist-col">${histOptions}</select></label>
      </div>
      <div class="chart-grid">
        <div class="chart-box"><h4>Scatter - colored by which method flagged each row</h4><canvas id="chart-scatter"></canvas></div>
        <div class="chart-box"><h4>Distribution</h4><canvas id="chart-hist"></canvas></div>
        ${scoreCharts}
      </div>
    </div>`;
}

function wireVisualizations(data) {
  if (!data.raw_numeric || data.raw_numeric.rows.length === 0) return;
  const scatterX = document.getElementById("scatter-x");
  const scatterY = document.getElementById("scatter-y");
  const histCol = document.getElementById("hist-col");
  if (!scatterX) return;

  function redrawScatter() {
    const idx = activeCharts.findIndex((c) => c.canvas.id === "chart-scatter");
    if (idx !== -1) activeCharts.splice(idx, 1)[0].destroy();
    const chart = buildScatterChart(
      document.getElementById("chart-scatter"),
      data.raw_numeric,
      data.flagged_by || {},
      scatterX.value,
      scatterY.value
    );
    activeCharts.push(chart);
  }
  function redrawHist() {
    const idx = activeCharts.findIndex((c) => c.canvas.id === "chart-hist");
    if (idx !== -1) activeCharts.splice(idx, 1)[0].destroy();
    const chart = buildHistogram(document.getElementById("chart-hist"), data.raw_numeric, histCol.value);
    activeCharts.push(chart);
  }

  scatterX.addEventListener("change", redrawScatter);
  scatterY.addEventListener("change", redrawScatter);
  histCol.addEventListener("change", redrawHist);

  redrawScatter();
  redrawHist();

  if (data.results) {
    Object.entries(data.results).forEach(([name, result]) => {
      const canvas = document.getElementById(`chart-score-${name}`);
      if (canvas && result.flagged.rows.length > 0) {
        activeCharts.push(buildScoreChart(canvas, name, result));
      }
    });
  }
}

// ---------------------------------------------------------------------------
// Results rendering
// ---------------------------------------------------------------------------
function detectorLabel(name) {
  return name === "isolation_forest" ? "Isolation Forest" : "KNN";
}

function modelSettingsLine(settings) {
  if (!settings) return "";
  if (settings.method === "knn") {
    return `Model: KNN (k=${settings.k}), standardised features. Rows with a distance above ${settings.score_threshold.toFixed(4)} are flagged.`;
  }
  return `Model: IsolationForest with ${settings.n_estimators} trees. Rows scoring below ${settings.score_threshold.toFixed(4)} are flagged.`;
}

function renderDetector(name, result) {
  const parts = [`<h3>${detectorLabel(name)}</h3>`];
  if (result.model_settings) parts.push(`<div class="model-line">${modelSettingsLine(result.model_settings)}</div>`);
  if (result.dropped_columns.length) {
    parts.push(`<p class="note-line">Excluded column(s) with no numeric data at all: ${result.dropped_columns.join(", ")}</p>`);
  }
  parts.push(`<div class="stat-row"><span>Scored <b>${result.scored_rows}</b> of <b>${result.total_rows}</b> rows</span>`);
  if (result.imputed && result.imputed_row_count > 0) {
    const methodLabel = result.impute_method === "knn" ? "KNN imputation" : "the column median";
    parts.push(`<span>Filled missing values in <b>${result.imputed_row_count}</b> row(s) with ${methodLabel}</span>`);
  } else if (!result.imputed && result.skipped_rows > 0) {
    parts.push(`<span>Skipped <b>${result.skipped_rows}</b> row(s) with missing values</span>`);
  }
  parts.push(`<span>Flagged <b>${result.flagged_count}</b> outlier row(s)</span></div>`);
  parts.push(renderTableCard(null, result.flagged, { filename: `${name}_flagged.csv` }));
  return parts.join("\n");
}

function renderComparison(comparison) {
  const parts = [`<h2>Comparison - Isolation Forest vs KNN</h2>`];
  parts.push(
    `<div class="stat-tiles">` +
      `<div class="stat-tile"><span class="tile-value">${comparison.isolation_forest_count}</span><span class="tile-label">Isolation Forest flagged</span></div>` +
      `<div class="stat-tile"><span class="tile-value">${comparison.knn_count}</span><span class="tile-label">KNN flagged</span></div>` +
      `<div class="stat-tile"><span class="tile-value">${comparison.both_count}</span><span class="tile-label">Flagged by both</span></div>` +
      `<div class="stat-tile"><span class="tile-value">${comparison.union_count}</span><span class="tile-label">Distinct rows total</span></div>` +
      (comparison.agreement !== null
        ? `<div class="stat-tile"><span class="tile-value">${(comparison.agreement * 100).toFixed(0)}%</span><span class="tile-label">Agreement</span></div>`
        : "") +
      (comparison.rank_correlation !== null
        ? `<div class="stat-tile"><span class="tile-value">${comparison.rank_correlation.toFixed(3)}</span><span class="tile-label">Score rank correlation</span></div>`
        : "") +
      `</div>`
  );
  parts.push(`<p class="note-line">Rows flagged by both methods are the high-confidence outliers, shown first and highlighted.</p>`);
  parts.push(
    renderTableCard(null, comparison.consensus, {
      rowClass: (row) => (row.flagged_by === "both" ? "flagged-both" : ""),
      filename: "comparison.csv",
    })
  );
  return parts.join("\n");
}

function renderImputationComparison(imputationComparison) {
  const active = imputationComparison.active_method === "knn" ? "KNN" : "median";
  const other = imputationComparison.active_method === "knn" ? "median" : "KNN";
  const parts = [`<h2>Imputation Comparison - Median vs KNN</h2>`];
  parts.push(
    `<p class="note-line">Scoring used <b>${active}</b> imputation. For every originally-missing cell, here is what ${active} filled in versus what ${other} would have filled in instead.</p>`
  );
  parts.push(renderTableCard(null, imputationComparison.table, { showIndex: true, filename: "imputation_comparison.csv" }));
  return parts.join("\n");
}

function render(data) {
  Object.keys(tableState).forEach((k) => delete tableState[k]);
  destroyCharts();
  const parts = [];

  const missingTotal = data.columns_info.rows.reduce((sum, r) => sum + (r.missing || 0), 0);
  const numericCount = data.numeric_summary ? data.numeric_summary.rows.length : 0;

  parts.push(`<div class="card"><h2>Dataset Overview</h2>`);
  parts.push(
    `<div class="stat-tiles">` +
      `<div class="stat-tile"><span class="tile-value">${data.rows}</span><span class="tile-label">Rows</span></div>` +
      `<div class="stat-tile"><span class="tile-value">${data.columns}</span><span class="tile-label">Columns</span></div>` +
      `<div class="stat-tile"><span class="tile-value">${numericCount}</span><span class="tile-label">Numeric columns</span></div>` +
      `<div class="stat-tile"><span class="tile-value">${missingTotal}</span><span class="tile-label">Missing cells</span></div>` +
      `</div>`
  );
  parts.push(renderTableCard("Column dtypes &amp; missing values", data.columns_info, { filename: "columns_info.csv" }));
  parts.push(`</div>`);

  if (!data.has_numeric) {
    parts.push(`<div class="card"><p class="note-line">No numeric columns found - statistics and outlier detection were skipped.</p></div>`);
    resultsEl.innerHTML = parts.join("\n");
    resultsEl.classList.remove("hidden");
    drawAllTables();
    return;
  }

  parts.push(`<div class="card"><h2>Numeric Column Statistics</h2>`);
  parts.push(renderTableCard("Central tendency, spread &amp; kurtosis", data.numeric_summary, { filename: "numeric_summary.csv" }));
  parts.push(renderTableCard("Five-point summary", data.five_point_summary, { filename: "five_point_summary.csv" }));
  parts.push(`</div>`);

  parts.push(`<div class="card"><h2>Covariance Matrix</h2>`);
  parts.push(renderTableCard(null, data.covariance_matrix, { filename: "covariance_matrix.csv" }));
  parts.push(`</div>`);

  if (data.imputation_comparison) {
    parts.push(`<div class="card">${renderImputationComparison(data.imputation_comparison)}</div>`);
  }

  parts.push(renderVisualizations(data));

  parts.push(`<div class="card"><h2>Outlier Detection</h2>`);
  Object.entries(data.results).forEach(([name, result]) => {
    parts.push(renderDetector(name, result));
  });
  parts.push(`</div>`);

  if (data.comparison) {
    parts.push(`<div class="card">${renderComparison(data.comparison)}</div>`);
  }

  resultsEl.innerHTML = parts.join("\n");
  resultsEl.classList.remove("hidden");
  drawAllTables();
  wireVisualizations(data);
}

// ---------------------------------------------------------------------------
// Analyze
// ---------------------------------------------------------------------------
function setLoading(isLoading) {
  analyzeBtn.disabled = isLoading;
  analyzeBtn.querySelector(".spinner").classList.toggle("hidden", !isLoading);
  analyzeBtn.querySelector(".btn-label").textContent = isLoading ? "Analyzing..." : "Analyze";
}

analyzeBtn.addEventListener("click", async () => {
  if (!currentFile) {
    showStatus("error", "Choose a CSV file first, or pick one of the samples.");
    return;
  }

  const form = new FormData();
  form.append("file", currentFile);
  form.append("method", methodSelect.value);
  form.append("contamination", document.getElementById("opt-contamination").value);
  form.append("k", document.getElementById("opt-k").value);
  form.append("impute", document.getElementById("opt-impute").checked ? "true" : "false");
  form.append("impute_method", imputeMethodSelect.value);
  form.append("impute_k", document.getElementById("opt-impute-k").value);

  setLoading(true);
  resultsEl.classList.add("hidden");
  showStatus("loading", "Analyzing...");

  try {
    const resp = await fetch("/api/analyze", { method: "POST", body: form });
    const data = await resp.json();
    if (!resp.ok) {
      showStatus("error", data.error || "Something went wrong.");
      return;
    }
    showStatus("", "");
    render(data);
  } catch (err) {
    showStatus("error", "Could not reach the server. Please try again.");
  } finally {
    setLoading(false);
  }
});

`````

### FILE: README.md

`````markdown
# Automated Data Health & Profiling Dashboard

A tool that reads an arbitrary CSV file, reports its statistical health, and
flags multivariate outliers using two unsupervised machine learning
methods - **Isolation Forest** and **KNN (k-nearest neighbours)** - then
compares what each one found. Available as both a command-line tool and a
browser-based UI.

## What it does

1. Reads a CSV and automatically splits columns into numeric vs. non-numeric
   (no manual schema needed).
2. Reports descriptive statistics per numeric column: mean, median, mode,
   variance, standard deviation, kurtosis, and a five-point summary, plus the
   covariance matrix across all numeric columns - computed on the raw,
   un-modified data.
3. Fills missing numeric values with each column's median in a *separate
   working copy* used only for scoring (`--no-impute` to disable).
4. Scores every row with Isolation Forest and/or KNN, flags the most unusual
   rows, and explains *why* each one was flagged (which column(s) deviated
   most, and by how many standard deviations).
5. Compares the two methods: rows both flag are high-confidence outliers;
   rows only one flags are worth a second look.

## Project structure

```
cli.py              entry point for the command-line tool
stats.py             descriptive statistics (Phase 1)
preprocessing.py     median imputation
ml_processing.py      Isolation Forest + KNN outlier detection and comparison
app.py               Flask web app - imports the same three modules above,
                     so the browser UI and the CLI always produce identical
                     results
static/              browser frontend (plain HTML/CSS/JS, no build step)
sample_*.csv         test fixtures (clean, messy, edge case, 200-row with
                     planted outliers)
```

The web app does not duplicate any logic - `app.py` calls the exact same
`stats.py`, `preprocessing.py`, and `ml_processing.py` functions the CLI
uses.

## Running the CLI

```bash
pip install -r requirements.txt
python cli.py sample_200.csv                              # both methods + comparison
python cli.py sample_200.csv --method knn --k 7
python cli.py sample_200.csv --method isolation_forest
python cli.py sample_200.csv --contamination 0.1
python cli.py sample_200.csv --no-impute
```

## Running the web UI locally

```bash
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000, upload a CSV (or click one of the sample
buttons), choose options, and click **Analyze**.

## Deploying to Vercel

This repo is set up for Vercel's Python runtime with zero extra config:

1. Push this repo to GitHub (already done if you're reading this on GitHub).
2. In the [Vercel dashboard](https://vercel.com/new), import the repo.
   Vercel detects Flask from `requirements.txt` + `app.py` automatically.
3. Deploy. No environment variables are required.

**One thing to know:** `pandas` + `numpy` + `scikit-learn` together are large
(around 400 MB installed), close to Vercel's 500 MB Python function limit.
`vercel.json` already excludes non-runtime files to help. If a deploy ever
fails on bundle size, Vercel's [Large Functions
beta](https://vercel.com/docs/functions/limitations#large-functions-beta)
(`VERCEL_SUPPORT_LARGE_FUNCTIONS=1`) raises the cap to 5 GB.

The demo caps uploads at 1 GB in `app.py` (`MAX_CONTENT_LENGTH`). Note that
this only governs the local/self-hosted server: Vercel enforces its own
request body size limit on Functions, well under 1 GB, so an upload that
large would be rejected by the platform before it ever reached this code
when deployed there. Locally, a file anywhere near that size could also take
a very long time to score - `IsolationForest` and the KNN detector's nearest-
neighbour search both get significantly slower as row count grows into the
millions.

## How well does it work?

Isolation Forest and KNN were checked against a 200-row synthetic dataset
(`sample_200.csv`) with 8 outliers deliberately planted and recorded
separately, at the default contamination of 0.05 (10 rows flagged each):

| Method | Rows flagged | Planted outliers found |
|---|---|---|
| Isolation Forest | 10 | 7 / 8 (87.5%) |
| KNN | 10 | 8 / 8 (100%) |
| Flagged by both | 8 | 7 planted + 1 naturally extreme row |

Isolation Forest missed one planted outlier because the dataset's random
missing-value step happened to blank out the two columns that made that row
unusual, and median imputation then made it look ordinary; KNN still caught
it through its other columns. At contamination 0.10, both methods find all
8 (with more rows flagged overall). This is a controlled test on synthetic
data with known answers - on real, unlabeled data there is no ground truth
to check a flag against, which is exactly why the tool reports both methods
and where they agree rather than a single verdict.

## What's not built yet

- Categorical encoding and feature scaling ahead of Isolation Forest (KNN
  already standardises its own features).
- Exporting results to a file (PDF/HTML/CSV) - both the CLI and the web UI
  are display-only right now.
- A formal automated test suite (current testing is manual, via the sample
  CSVs and a one-off recall check against `sample_200.csv`'s planted
  outliers).
- Chunked reading for very large files.

## References

- Liu, F. T., Ting, K. M., & Zhou, Z.-H. (2008). Isolation Forest. *IEEE
  ICDM*, 413-422.
- Ramaswamy, S., Rastogi, R., & Shim, K. (2000). Efficient algorithms for
  mining outliers from large data sets. *ACM SIGMOD*, 427-438.
- Pedregosa, F. et al. (2011). Scikit-learn: Machine Learning in Python.
  *JMLR*, 12, 2825-2830.

`````

### FILE: sample_numeric.csv

`````csv
id,age,income,tenure_years,score
1,25,50000,1.5,7.5
2,34,52000,3.2,8.1
3,31,48000,2.0,6.9
4,45,61000,10.5,7.8
5,29,,4.1,5.4
6,38,59500,6.0,7.2
7,52,250000,20.0,9.9
8,27,53000,1.0,7.0
9,33,54500,3.5,6.8
10,41,-999,5.5,1.0
11,36,58000,7.0,7.4
12,,,,
13,30,55000,2.5,7.1
14,48,62500,15.0,8.0
15,26,51500,0.8,6.7

`````

### FILE: sample_messy.csv

`````csv
id,age,income,city,notes,score
1,25,50000,New York,ok,7.5
2,,52000,Boston,,8.1
3,31,abc,Chicago,mixed type in income,6.9
4,45,61000,New York,,7.8
5,29,,Boston,missing income,5.4
6,38,59500,,unexpected empty city,7.2
7,52,250000,Chicago,high income outlier,9.9
8,27,53000,Boston,,7.0
9,33,54500,New York,,6.8
10,41,-999,Chicago,weird sentinel value,1.0
11,36,58000,Boston,,7.4
12,,,New York,fully missing numerics,
13,30,55000,Chicago,,7.1
14,48,62500,Boston,,8.0
15,26,51500,New York,,6.7
extra_col,unexpected header row style,,,,

`````

### FILE: sample_fully_missing_col.csv

`````csv
id,age,ghost_col,score
1,25,,7.5
2,34,,8.1
3,31,,6.9
4,45,,7.8
5,,,5.4

`````

### FILE: sample_200.csv

`````csv
id,age,income,tenure_years,score,city
1,31.0,60423.11,4.8,8.0,Seattle
2,27.0,57929.1,6.3,6.9,New York
3,45.0,-999.0,4.5,7.3,New York
4,41.0,52898.3,0.0,7.3,Chicago
5,,59258.36,4.4,,Seattle
6,41.0,78273.17,4.3,8.7,New York
7,36.0,62173.83,3.4,8.5,Boston
8,22.0,52897.96,3.3,5.9,Austin
9,,63790.85,4.5,4.9,Seattle
10,40.0,,2.3,6.6,Austin
11,42.0,72992.57,5.7,6.7,New York
12,24.0,47961.56,4.9,4.0,Boston
13,51.0,72784.44,7.5,4.9,Chicago
14,41.0,74647.95,7.0,4.8,Austin
15,24.0,60212.69,4.8,5.6,Chicago
16,49.0,79307.5,4.7,8.5,New York
17,32.0,59921.2,4.3,7.6,Boston
18,28.0,,5.0,6.7,Chicago
19,31.0,79710.44,6.4,9.7,Chicago
20,42.0,75253.33,0.7,7.8,Seattle
21,34.0,72284.9,8.8,7.1,Boston
22,58.0,86180.61,5.8,4.1,Chicago
23,37.0,70024.64,5.2,4.6,Boston
24,36.0,79165.03,8.7,8.1,Seattle
25,36.0,63290.31,,7.1,Chicago
26,35.0,72377.84,6.5,9.2,Seattle
27,45.0,75871.11,0.0,6.7,Chicago
28,32.0,70725.61,4.7,8.4,Chicago
29,21.0,65490.48,9.2,7.8,New York
30,36.0,69887.7,0.0,7.5,Boston
31,20.799437199776506,234715.53838139257,2.9,7.2,Boston
32,27.0,,3.0,5.8,Chicago
33,27.0,59125.92,3.5,8.6,Boston
34,25.0,53209.3,0.7,6.4,Boston
35,42.0,90472.93,9.5,5.8,Austin
36,39.0,67977.55,2.6,6.4,Seattle
37,47.0,81030.27,0.0,7.4,New York
38,44.0,63467.2,0.2,8.2,Seattle
39,39.0,74538.48,22.971716409351906,1.2770019741033058,Chicago
40,37.0,73609.96,4.2,5.0,Boston
41,28.0,68188.31,2.4,5.5,Austin
42,30.0,59299.37,0.5,,Chicago
43,22.0,56633.45,3.3,4.8,New York
44,37.0,82564.71,7.5,4.0,New York
45,38.0,88924.62,,8.8,Chicago
46,41.0,67864.53,,5.1,Boston
47,37.0,54588.85,0.1,6.8,Seattle
48,34.0,68394.22,4.2,5.4,Boston
49,32.0,64948.18,,10.0,Seattle
50,35.0,71777.43,7.2,9.3,Seattle
51,31.0,64463.48,,6.5,Austin
52,44.0,77846.6,2.5,7.6,Austin
53,35.0,60219.77,1.9,7.9,New York
54,40.0,77438.03,7.6,7.5,New York
55,24.0,54803.27,5.9,7.1,Seattle
56,38.0,58006.91,1.4,,Seattle
57,42.0,72635.17,3.5,6.2,Seattle
58,,56692.62,4.9,8.5,Chicago
59,23.0,47455.45,4.1,7.4,Chicago
60,27.0,56636.36,2.9,5.7,Austin
61,39.0,,3.1,6.4,Seattle
62,28.0,62598.42,3.6,8.6,Chicago
63,23.0,58133.4,5.3,7.0,Boston
64,36.0,78976.0,8.4,5.8,Seattle
65,34.0,57396.6,0.0,,Chicago
66,32.0,73627.79,2.6,7.7,Chicago
67,32.0,57037.33,0.0,9.3,Seattle
68,40.0,75592.66,5.0,6.8,Chicago
69,38.0,68486.38,n/a,7.0,Austin
70,38.0,54081.19,0.0,8.3,New York
71,32.0,69549.12,6.8,8.6,Chicago
72,31.0,64617.87,3.1,5.4,New York
73,23.0,,4.5,6.0,Boston
74,28.0,54031.49,3.5,5.6,New York
75,40.0,66158.61,1.9,7.7,Boston
76,32.0,64383.12,6.6,,New York
77,38.0,52255.13,0.0,5.8,Chicago
78,,65450.26,,6.5,Boston
79,25.0,56754.97,,7.7,Boston
80,27.0,74266.12,8.0,7.3,Chicago
81,31.0,52533.17,1.4,7.8,New York
82,34.0,70790.57,4.6,5.3,Austin
83,34.0,52800.23,1.9,7.1,Austin
84,26.0,54863.58,6.1,4.7,New York
85,36.0,59912.6,4.7,5.8,Austin
86,41.0,68295.7,5.4,6.9,Chicago
87,39.0,87321.51,11.6,6.5,Chicago
88,44.0,,0.0,6.5,New York
89,39.0,72621.97,3.7,7.9,New York
90,23.0,76206.08,9.2,9.2,Seattle
91,37.0,69380.73,2.6,5.3,Chicago
92,30.0,65599.29,0.0,7.8,Austin
93,32.0,64227.11,0.3,7.6,Austin
94,34.0,69549.19,4.5,6.7,Seattle
95,25.0,56851.83,,8.8,New York
96,34.0,70560.23,5.1,7.0,Boston
97,25.0,57286.25,1.8,8.0,Austin
98,42.0,69542.11,1.8,7.1,New York
99,37.0,69466.06,5.3,7.9,Boston
100,35.0,51641.64,1.4,4.8,Chicago
101,,,3.8,8.4,Chicago
102,33.0,82486.04,4.8,6.8,Boston
103,38.0,70844.79,6.2,8.9,Boston
104,22.584488329694523,226023.73873898856,3.6,7.4,Austin
105,38.0,71206.96,3.1,3.9,New York
106,43.0,75187.55,5.9,6.2,Chicago
107,40.0,72167.34,2.4,7.7,Seattle
108,37.0,66863.17,2.9,9.4,Boston
109,36.0,,0.7,7.5,New York
110,28.0,51806.79,0.8,,Seattle
111,36.0,76894.84,6.5,6.7,Austin
112,31.0,,3.3,7.8,Austin
113,40.0,77311.72,3.2,7.4,Seattle
114,52.0,87606.85,7.0,8.0,Boston
115,37.0,71223.97,0.0,7.2,New York
116,26.0,53467.22,3.6,7.6,Boston
117,,91737.55,12.7,7.2,Boston
118,30.0,54311.24,4.0,9.2,Boston
119,43.0,68544.82,0.0,6.6,Chicago
120,28.0,66886.74,7.0,5.3,Seattle
121,32.0,72761.88,1.0,5.6,Austin
122,34.0,66102.76,3.3,6.4,Seattle
123,39.0,67890.7,3.0,6.0,Austin
124,25.0,55875.22,5.6,6.7,Chicago
125,33.0,63914.0,1.0,6.8,Boston
126,32.0,67733.11,,10.0,Chicago
127,28.0,51921.17,3.0,7.7,Austin
128,33.0,57639.03,0.8,5.7,Seattle
129,32.0,73259.31,,7.7,Chicago
130,43.0,69706.42,4.8,8.1,Boston
131,36.0,64480.41,4.1,5.1,Boston
132,38.0,79135.3,5.6,7.9,New York
133,37.0,75561.07,9.5,4.8,Seattle
134,34.0,63248.78,5.8,7.7,Chicago
135,33.0,70223.62,0.5,5.7,Austin
136,30.0,59025.61,4.7,7.0,New York
137,29.0,65905.77,5.2,7.8,Austin
138,32.0,69379.38,8.5,7.6,Chicago
139,37.0,68211.91,7.9,6.9,New York
140,39.0,81661.95,10.3,5.3,Seattle
141,52.0,70556.74,0.0,9.1,Austin
142,30.0,61520.33,2.2,9.3,New York
143,28.0,55614.57,7.6,4.5,Boston
144,32.0,57844.89,0.0,8.2,New York
145,60.89746036173044,,0.0,,Seattle
146,25.0,62189.06,5.7,7.0,Chicago
147,46.0,79701.94,6.3,5.1,Seattle
148,35.0,71349.96,5.6,8.3,Chicago
149,32.0,80783.17,9.2,8.4,Boston
150,36.0,64928.83,4.7,5.8,Boston
151,45.0,62490.47,4.3,6.9,Chicago
152,32.0,58599.79,3.2,7.0,Austin
153,44.0,68970.0,2.0,6.6,Austin
154,42.0,68956.89,6.7,5.7,Austin
155,49.0,66765.75,0.0,6.0,New York
156,26.0,58307.53,,7.4,Seattle
157,47.0,70489.45,5.4,7.5,New York
158,34.0,63323.79,0.0,4.1,Boston
159,48.0,89086.89,7.0,6.5,Boston
160,28.0,66879.73,8.8,7.1,New York
161,27.0,67780.66,8.2,6.2,Austin
162,32.0,70384.66,5.4,6.3,New York
163,48.0,82866.7,0.0,6.8,New York
164,35.0,70381.81,4.2,8.9,Boston
165,42.0,82036.88,4.9,8.0,New York
166,19.0,50227.0,0.0,6.2,Chicago
167,28.0,52474.3,0.8,7.8,Boston
168,39.0,76692.12,8.0,8.8,Seattle
169,40.0,74269.78,1.8,6.6,New York
170,30.0,71396.86,9.2,5.7,Boston
171,22.0,-999.0,2.3,5.7,Austin
172,33.0,74107.44,5.3,5.9,Austin
173,33.0,59927.45,4.0,3.7,New York
174,36.0,75943.28,10.4,6.6,Seattle
175,35.0,72471.52,1.9,8.9,Chicago
176,36.0,63944.75,1.5,8.0,Austin
177,30.0,67411.14,6.3,7.4,Seattle
178,41.0,72664.45,5.2,7.5,Austin
179,37.0,,5.0,7.7,Austin
180,31.0,69372.21,6.6,7.3,Chicago
181,27.0,58724.83,0.4,7.2,Boston
182,25.0,58988.91,3.8,8.0,New York
183,48.0,86317.12,3.4,5.6,Seattle
184,42.0,80735.96,4.2,6.3,Chicago
185,38.0,62532.5,1.5,6.3,Seattle
186,38.0,63967.37,2.0,8.0,Seattle
187,30.0,59171.53,0.0,9.7,Austin
188,38.0,66084.25,7.5,7.0,Boston
189,39.0,74643.51,3.7,6.4,Austin
190,28.0,59043.82,19.851778678059176,1.2697178041019355,Austin
191,34.0,52766.78,0.7,6.2,Austin
192,64.37287569927786,166966.10728682805,0.0,5.7,Chicago
193,47.0,86683.78,1.6,7.3,Austin
194,32.0,69682.51,8.4,8.2,Austin
195,41.0,62384.98,3.0,,Austin
196,27.0,67389.2,6.5,6.6,Austin
197,31.0,77173.39,5.1,7.6,Chicago
198,32.0,63701.9,4.7,6.3,Chicago
199,40.0,72326.47,6.3,8.3,Boston
200,36.0,70171.07,11.0,7.3,New York

`````

## Appendix B. Generator for `sample_200.csv`

Reproduces the file byte-for-byte. Prints the ground-truth planted ids
`[3, 31, 39, 104, 145, 171, 190, 192]`. Run it, then compare
`sample_200_regenerated.csv` with `sample_200.csv`.

### FILE: gen_sample_200.py

`````python
"""Regenerates sample_200.csv: 200 rows, 8 planted multivariate outliers,
random missing values, one "n/a" text cell, rows shuffled, ids reassigned."""
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
n = 200
cities = ["New York", "Boston", "Chicago", "Austin", "Seattle"]

age = np.clip(rng.normal(35, 8, n).round(), 18, 65).astype(float)
tenure_years = np.clip(rng.normal(4, 3, n), 0, None).round(1)
income = (30000 + age * 900 + tenure_years * 1500 + rng.normal(0, 6000, n)).round(2)
score = np.clip(rng.normal(7, 1.3, n), 0, 10).round(1)
city = rng.choice(cities, n)

df = pd.DataFrame({"id": np.arange(1, n + 1), "age": age, "income": income,
                   "tenure_years": tenure_years, "score": score, "city": city})

# 8 planted outliers, 4 patterns x 2
outlier_idx = rng.choice(df.index, size=8, replace=False)
planted_old_ids = set()
for i, idx in enumerate(outlier_idx):
    planted_old_ids.add(idx + 1)
    kind = i % 4
    if kind == 0:    # very young, very high income
        df.loc[idx, "age"] = rng.uniform(19, 23)
        df.loc[idx, "income"] = rng.uniform(220000, 280000)
    elif kind == 1:  # sentinel-style negative income
        df.loc[idx, "income"] = -999
    elif kind == 2:  # long tenure, very low score
        df.loc[idx, "tenure_years"] = rng.uniform(18, 25)
        df.loc[idx, "score"] = rng.uniform(0, 1.5)
    else:            # old, zero tenure, high income
        df.loc[idx, "age"] = rng.uniform(60, 65)
        df.loc[idx, "tenure_years"] = 0.0
        df.loc[idx, "income"] = rng.uniform(150000, 200000)

# random missing values (6-11 per numeric column)
for col in ["age", "income", "tenure_years", "score"]:
    miss_idx = rng.choice(df.index, size=rng.integers(6, 12), replace=False)
    df.loc[miss_idx, col] = np.nan

# one text cell in a numeric column (pandas reads "n/a" back as NaN)
mixed_idx = rng.choice(df.index, size=1, replace=False)
df["tenure_years"] = df["tenure_years"].astype(object)
df.loc[mixed_idx, "tenure_years"] = "n/a"

df = df.sample(frac=1, random_state=7).reset_index(drop=True)
shuffled_old = df["id"].copy()
df["id"] = np.arange(1, n + 1)
planted_new_ids = sorted(int(new) for new, old in zip(df["id"], shuffled_old) if old in planted_old_ids)

if __name__ == "__main__":
    df.to_csv("sample_200_regenerated.csv", index=False)
    print("planted outlier ids (ground truth):", planted_new_ids)

`````
