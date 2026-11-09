# 15. Putting it online (Vercel + Streamlit Community Cloud)

## The short answer

**The dashboard can't run on Vercel by itself.** Vercel is built for websites and small functions that
run for a few seconds and stop. A Streamlit dashboard is a Python program that has to *stay running*,
keep a live connection to each visitor's browser, and hold 300 MB to 2 GB of data in memory while you
click around. The Python libraries alone (pandas, scipy, scikit-learn) are also close to Vercel's size
limit for functions.

So the setup is:

| Piece | Where | Cost | What it is |
|---|---|---|---|
| **Live dashboard** | **Streamlit Community Cloud** | Free | The full app: upload data, review cases, change settings |
| **Landing page** | **Vercel** | Free | A fast public page with headline results and charts, plus a button that opens the dashboard |

```
judges / anyone ──▶ trustloop.vercel.app (Vercel: instant, never sleeps)
                         │  "Open the live dashboard"
                         ▼
                    trustloop.streamlit.app (Streamlit Cloud: the real app)
```

Both deploy straight from your GitHub repo, and both update automatically when you push changes.
Everything they need (`vercel.json`, `site/`, `.streamlit/config.toml`, `requirements.txt`) is
already in the repo.

---

## Part A: Deploy the dashboard on Streamlit Community Cloud (about 10 minutes)

1. Go to **https://share.streamlit.io** and click **Continue with GitHub**. Sign in with the GitHub
   account that owns `guransh111/merchantfiling`, and allow Streamlit to see your repositories.
2. Click **Create app** (top right), then **Deploy a public app from GitHub**.
3. Fill in:
   - **Repository:** `guransh111/merchantfiling`
   - **Branch:** `main`
   - **Main file path:** `app/dashboard.py`
   - **App URL:** choose a name, e.g. `trustloop` → `https://trustloop.streamlit.app`
4. Click **Advanced settings** and choose **Python 3.12**. Leave secrets empty.
5. Click **Deploy**. The first build installs the libraries and takes 3 to 5 minutes. You'll see the
   log scrolling; that's normal.
6. When it opens, click **Overview** in the left menu. The first analysis takes about 10 seconds.

**Copy your app's URL**; you need it for Part B.

### Things to know about the free tier

- **It sleeps** after a while with no visitors. The next visitor sees a "wake up" button and waits
  about a minute. **Open it yourself 5 minutes before you present.**
- **Memory is about 1 GB.** The demo, uploads of a few hundred thousand payments, and the Generate page
  all work. The Generate page automatically caps the world at **300 merchants** when memory is tight
  (1,000 merchants needs ~2 GB; run that on your own laptop).
- **It's public by default.** Anyone with the link can open it. **Don't upload real, confidential
  merchant data to a public app.** In the app's settings (⋮ → Settings → Sharing) you can restrict it to
  specific email addresses.
- **Session data isn't saved.** Analyst decisions and uploads disappear when the session ends; use the
  download buttons to keep them.

---

## Part B: Deploy the landing page on Vercel (about 5 minutes)

1. Go to **https://vercel.com** and click **Sign up / Log in → Continue with GitHub**.
2. Click **Add New… → Project**. Find `merchantfiling` in the list and click **Import**.
3. On the configure screen:
   - **Framework Preset:** `Other` (the repo's `vercel.json` already says how to build)
   - Leave **Build Command** and **Output Directory** alone (they come from `vercel.json`)
   - Open **Environment Variables** and add:
     - Name `DASHBOARD_URL`, value: your Streamlit URL from Part A, e.g. `https://trustloop.streamlit.app`
4. Click **Deploy**. It takes under a minute. You get a URL like `https://merchantfiling.vercel.app`.
   You can rename it under **Settings → Domains**.
5. Open it and click **Open the live dashboard** to check the link.

If you change `DASHBOARD_URL` later: **Deployments → ⋯ on the latest one → Redeploy**. Environment
variables only take effect on a new build.

### What Vercel is doing (in case a judge asks)

`vercel.json` tells Vercel to run `site/build.sh`, which copies `site/index.html` and the charts from
`reports/` into a folder, fills in your dashboard link, and publishes it as a static website on
Vercel's global network. No Python runs on Vercel. When you re-run `python run_all.py` and push new
charts, Vercel rebuilds the page automatically.

---

## Part C: Updating

| You change… | What to do | What updates |
|---|---|---|
| Code or settings | `git push` | Streamlit Cloud redeploys in ~1 minute; Vercel rebuilds |
| Results (`python run_all.py`) | Commit `reports/` and the small `data/` files, then push | Both |
| The landing-page text | Edit `site/index.html`, push | Vercel |

## Alternatives if Streamlit Cloud isn't enough

| Option | Why you'd pick it |
|---|---|
| **Hugging Face Spaces** (Docker Space, free CPU tier) | Much more memory, so 1,000-merchant worlds fit |
| **Render / Railway** (paid, a few dollars a month) | Always on (no sleeping), private |
| **Your laptop** (`streamlit run app/dashboard.py`) | Most reliable for a live presentation, with no internet dependence |

**For the competition itself:** present from your laptop if you can (file 08), and use the
Vercel link in your deck and email so judges can explore afterwards.

## Could the whole thing ever run on Vercel?

Only by rebuilding the dashboard as a JavaScript website (e.g. Next.js) and moving the analysis into a
separate Python service hosted elsewhere, because the analysis would still need a server with enough memory.
That's weeks of work for no benefit to the competition, so the split above is the sensible choice.
