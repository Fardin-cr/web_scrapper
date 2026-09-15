"""
model.py — Model 3: Market Segment Discovery (K-Means Clustering)
=================================================================
Features used : price, original_price, discount, review_count
Preprocessing : StandardScaler + log1p on review_count
K Selection   : Elbow Method + Silhouette Score (K = 3 to 8)
Output        : reports/elbow_silhouette.png
                reports/pca_scatter.png
                Cluster labels saved back to SQLite
"""
import os, sqlite3
import numpy  as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.cluster        import KMeans
from sklearn.decomposition  import PCA
from sklearn.metrics        import silhouette_score, silhouette_samples

DB      = "data/steam_games.db"
OUT_DIR = "reports"
os.makedirs(OUT_DIR, exist_ok=True)

PALETTE = ["#7C3AED","#4ADE80","#F43F5E","#FBBF24","#60A5FA","#FB923C","#E879F9","#34D399"]
DARK    = "#0F172A"
SURFACE = "#1E293B"
TEXT    = "#E2E8F0"
MUTED   = "#94A3B8"

# ── 1. Load ────────────────────────────────────────────────────────────────
def load():
    if not os.path.exists(DB):
        raise FileNotFoundError("No database found. Run scraper first.")
    conn = sqlite3.connect(DB)
    df   = pd.read_sql("SELECT * FROM games", conn)
    conn.close()
    print(f"[INFO] Loaded {len(df):,} games.")
    return df

# ── 2. Preprocess (Data Cleaning for model) ────────────────────────────────
FEATS = ["price", "original_price", "discount", "review_count"]

def preprocess(df):
    for col in FEATS:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    # Remove extreme outliers (top 5%) so they don't distort clusters
    for col in ["price", "original_price", "review_count"]:
        df[col] = df[col].clip(upper=df[col].quantile(0.95))
    df["log_reviews"] = np.log1p(df["review_count"])
    scaled = StandardScaler().fit_transform(
        df[["price","original_price","discount","log_reviews"]])
    print(f"[INFO] Preprocessed {len(df):,} records.")
    return df, scaled

# ── 3. Choose optimal K ────────────────────────────────────────────────────
def choose_k(X):
    ks, inertias, sils = range(3, 9), [], []
    print("[INFO] Running Elbow + Silhouette (K=3 to 8)...")
    for k in ks:
        km  = KMeans(n_clusters=k, random_state=42, n_init=10)
        lbl = km.fit_predict(X)
        inertias.append(km.inertia_)
        sils.append(silhouette_score(X, lbl))
        print(f"       K={k}  inertia={km.inertia_:,.0f}  silhouette={sils[-1]:.4f}")
    best_k = list(ks)[int(np.argmax(sils))]
    print(f"[INFO] Optimal K = {best_k}  (silhouette={max(sils):.4f})")
    return best_k, list(ks), inertias, sils

# ── 4. Plot: Elbow + Silhouette ────────────────────────────────────────────
def plot_elbow(ks, inertias, sils, best_k):
    plt.rcParams.update({"figure.facecolor": DARK, "axes.facecolor": SURFACE,
                          "axes.edgecolor": "#334155", "text.color": TEXT,
                          "xtick.color": MUTED, "ytick.color": MUTED, "font.family":"sans-serif"})
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("K-Means: Elbow Method & Silhouette Scores", color=TEXT, fontweight="bold")

    a1.plot(ks, inertias, "o-", color="#7C3AED", lw=2, ms=7, mfc="#A78BFA")
    a1.axvline(best_k, color="#4ADE80", ls="--", lw=1.4, label=f"Best K={best_k}")
    a1.set(title="Elbow Curve (Inertia)", xlabel="K", ylabel="Inertia (WCSS)")
    a1.legend(labelcolor=TEXT, framealpha=0.2); a1.grid(alpha=0.3)

    cols = [PALETTE[i] for i in range(len(ks))]
    bars = a2.bar(ks, sils, color=cols, alpha=0.85, width=0.6)
    a2.axvline(best_k, color="#4ADE80", ls="--", lw=1.4, label=f"Best K={best_k}")
    for b, s in zip(bars, sils):
        a2.text(b.get_x()+b.get_width()/2, b.get_height()+.005,
                f"{s:.3f}", ha="center", fontsize=9, color=TEXT, fontweight="bold")
    a2.set(title="Silhouette Score per K", xlabel="K", ylabel="Silhouette Score")
    a2.legend(labelcolor=TEXT, framealpha=0.2); a2.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    path = os.path.join(OUT_DIR, "elbow_silhouette.png")
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=DARK)
    plt.close(); print(f"[PLOT] Saved -> {path}")

# ── 5. Plot: PCA Scatter ───────────────────────────────────────────────────
def plot_pca(X, df, best_k):
    pca  = PCA(n_components=2, random_state=42)
    X2d  = pca.fit_transform(X)
    var  = pca.explained_variance_ratio_
    segs = df["segment"].unique()
    colors = {s: PALETTE[i % len(PALETTE)] for i, s in enumerate(segs)}

    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor(DARK); ax.set_facecolor(SURFACE)
    for seg in segs:
        m = df["segment"] == seg
        ax.scatter(X2d[m, 0], X2d[m, 1], c=colors[seg], s=18,
                   alpha=0.55, label=seg, edgecolors="none", rasterized=True)
    ax.set(title=f"Market Segments - PCA Projection (K={best_k})\n"
                 f"PC1={var[0]*100:.1f}%  PC2={var[1]*100:.1f}% variance",
           xlabel="PC1", ylabel="PC2")
    ax.title.set_color(TEXT); ax.xaxis.label.set_color(MUTED); ax.yaxis.label.set_color(MUTED)
    lg = ax.legend(title="Segment", framealpha=0.15, labelcolor=TEXT, fontsize=8)
    lg.get_title().set_color(MUTED)
    ax.grid(alpha=0.2)
    fig.tight_layout()
    path = os.path.join(OUT_DIR, "pca_scatter.png")
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=DARK)
    plt.close(); print(f"[PLOT] Saved -> {path}")

# ── 6. Name clusters ───────────────────────────────────────────────────────
def name_clusters(df, labels, k):
    df = df.copy(); df["cluster"] = labels
    prof = []
    for c in range(k):
        s = df[df["cluster"] == c]
        prof.append({"id": c, "count": len(s),
                     "med_price": s["price"].median(),
                     "pct_free":  (s["price"]==0).mean()*100,
                     "med_rev":   s["review_count"].median()})
    prof = pd.DataFrame(prof).sort_values("med_price").reset_index(drop=True)
    names, seen = [], {}
    for _, r in prof.iterrows():
        n = ("Free-to-Play Powerhouses" if r.pct_free >= 35 else
             "Budget Indie"             if r.med_price < 3  else
             "Popular Mid-Range"        if r.med_price < 10 and r.med_rev > 1000 else
             "Niche / Emerging Titles"  if r.med_price < 15 else
             "Premium Blockbusters"     if r.med_rev > 5000 else
             "Premium / AAA")
        seen[n] = seen.get(n, 0) + 1
        names.append(n if seen[n] == 1 else f"{n} ({seen[n]})")
    prof["segment"] = names
    df["segment"] = df["cluster"].map(dict(zip(prof["id"], prof["segment"])))
    return df, prof

# ── 7. Save results ────────────────────────────────────────────────────────
def save(df, prof):
    conn = sqlite3.connect(DB)
    for col in ("cluster", "segment"):
        try: conn.execute(f"ALTER TABLE games ADD COLUMN {col} TEXT")
        except: pass
    for _, row in df.iterrows():
        conn.execute("UPDATE games SET cluster=?, segment=? WHERE app_id=?",
                     (str(row.get("cluster","")), str(row.get("segment","")), row["app_id"]))
    export_df = df.drop(columns=["scraped_at", "log_reviews"], errors="ignore")
    export_df.to_csv(os.path.join(OUT_DIR, "clustered_games.csv"), index=False, encoding="utf-8-sig")
    print("[SAVE] cluster + segment written to DB and CSV")
    print("\n" + "="*65)
    print("  MARKET SEGMENT SUMMARY")
    print("="*65)
    print(prof[["segment","count","med_price","pct_free","med_rev"]]
          .rename(columns={"med_price":"Med Price($)","pct_free":"% Free","med_rev":"Med Reviews"})
          .to_string(index=False))
    print("="*65)

# ── MAIN ───────────────────────────────────────────────────────────────────
def run():
    print("\n" + "="*65)
    print("  MODEL 3 - Market Segment Discovery (K-Means Clustering)")
    print("="*65)
    df            = load()
    df, X         = preprocess(df)
    best_k, ks, inertias, sils = choose_k(X)
    km            = KMeans(n_clusters=best_k, random_state=42, n_init=20)
    labels        = km.fit_predict(X)
    df, prof      = name_clusters(df, labels, best_k)
    plot_elbow(ks, inertias, sils, best_k)
    plot_pca(X, df, best_k)
    save(df, prof)
    print(f"\n[DONE] Reports saved to /{OUT_DIR}/\n")

if __name__ == "__main__":
    run()
