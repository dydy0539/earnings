# Verified IOMA and ERQI cloud enrichment

Run the existing **Earnings after close** workflow manually on `cursor/save-earnings-reports-2dbe`, choosing `mode: analyze`.

The GitHub-hosted runner selects the latest AM and latest BM HTML filenames independently, recomputes IOMA and same-basis margins from exact source-verified inputs, applies the 1.0 percentage-point / favorable-divergence selection rule, inserts the full prepared ERQI research, validates preservation, and commits the two reports in the repository root on the same branch. Validation JSON is saved under `analysis/`.

Research packets are dated and tied to the original report SHA-256 and exact filtered ticker order. A changed or newer report without a matching packet fails explicitly. This is a cloud calculation/publishing pipeline using primary-source research prepared by the research agent; it is **not** an autonomous model research service for future reports. No model API key is configured by this change. Existing scrape schedules are unchanged and can overwrite a report with a fresh scrape; rerun analysis only after verifying a matching packet. GitHub schedules execute from the default branch, while this manual run targets the requested feature branch.

The online Oct 20 AM report contains five filtered companies, unlike the nine-company local report. Online rows are authoritative for this run. AM ERQI covers NFLX and ISRG; BM covers GE and VICR. Missing ISRG Q3 cash statements and incomplete VICR royalty/cash detail are disclosed rather than filled with estimates. GE's cash definition and working-capital divergence are separately analyzed.

All screening amounts are quarterly consolidated USD millions. Source notes document adjusted revenue scope, bank net revenue and proxy-profit definitions. Signed IOMA is retained. Removing generated blocks and cells must restore original HTML byte-for-byte. Reruns do not duplicate generated cells or appendices. Rendered browser QA has not been claimed.
