# JoshysGakuGuide — automatic update starter

This starter converts the local HTML site into a GitHub Pages project and adds a scheduled source monitor.

## What it does

- Deploys `index.html` to GitHub Pages when code is pushed to `main`.
- Runs the source checker every 6 hours, plus a manual **Run workflow** button.
- Checks three community code pages and writes candidate code/status data to `data/updates.json`.
- Marks codes seen on two or more monitored sources as `reported_active`; one-source entries are `unverified`.
- Watches the Gakuran fighting-styles page for changes and flags changes for human review.

## Important limitations

- Third-party code pages disagree, and no public page can test redemption on your Roblox account.
- A code disappearing from a page does not prove it expired. The script therefore does not automatically mark a code expired.
- Awakening requirement changes are flagged for review. The script does not rewrite guide prose from a changed source because that could introduce incorrect requirements.
- The homepage now loads `data/updates.json` when hosted. It displays corroborated/unverified code candidates and an awakening-source change notice. Its original lists remain as a fallback until the first successful workflow run.
- GitHub scheduled workflows can be delayed and depend on the repository's default branch and Actions settings.

## Setup

1. Create or sign in to a GitHub account.
2. Create a new **public** repository named `JoshysGakuGuide`.
3. Extract this ZIP on your computer.
4. Upload all files and folders from this extracted folder to the repository root. Keep `.github/workflows/` and `scripts/` in their exact locations.
5. In the repository, open **Settings → Pages**. Under **Build and deployment**, choose **GitHub Actions**.
6. Open the **Actions** tab and enable workflows if GitHub asks.
7. Run **Check Gakuran codes and awakenings** once using **Run workflow**.
8. After the deployment workflow succeeds, open **Settings → Pages** to find your live website URL.

## Verification before relying on it

After the first workflow run, open `data/updates.json` and check that the source parsers found code candidates. If a source changes its page layout, the workflow log will show a warning and the prior data remains available. The awakening monitor detects source-page changes and flags them for human review; it does not invent or silently rewrite quest requirements. Do not call a code guaranteed valid until it has been redeemed successfully in-game.
