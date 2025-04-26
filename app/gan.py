import os
import pickle
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend to avoid Tkinter errors
import matplotlib.pyplot as plt
import seaborn as sns
from ctgan import CTGAN
from scipy.stats import ks_2samp
from sklearn.decomposition import PCA
from sklearn.preprocessing import QuantileTransformer
import warnings
import logging

from app import model_mappings

import time
def generate_synthetic_data(decrypted_file_path, username, filename, output_dir="app/static/Uploads"):
    """Generate synthetic data from the decrypted file, using or training a CTGAN model mapped by username and filename."""
    data = pd.read_csv(decrypted_file_path)

    # Standardize column names
    data.columns = (
        data.columns.str.strip()
        .str.replace(r"\s+", " ", regex=True)
        .str.replace(r"[^\w\s]", "", regex=True)
    )

    # Drop columns starting with 'Unnamed'
    unnamed_cols = [col for col in data.columns if col.startswith('Unnamed')]
    if unnamed_cols:
        data.drop(columns=unnamed_cols, inplace=True)

    # Drop unnecessary columns
    data.drop(columns=["Sl No", "Patient File No"], inplace=True, errors="ignore")

    # Convert PCOS YN
    if "PCOS YN" in data.columns:
        data["PCOS YN"] = data["PCOS YN"].replace({"Yes": 1, "No": 0}).astype(int)

    # Convert to numeric and fill missing values
    data = data.apply(pd.to_numeric, errors="coerce")
    data.fillna(data.median(numeric_only=True), inplace=True)

    special_cols = ["I betaHCGmIUmL", "II betaHCGmIUmL", "FSHmIUmL", "LHmIUmL", "Vit D3 ngmL"]
    target_col = "PCOS YN" if "PCOS YN" in data.columns else None
    numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()

    qt = QuantileTransformer(output_distribution="normal", random_state=42)
    data_scaled = data.copy()
    data_scaled[numeric_cols] = qt.fit_transform(data[numeric_cols])

    # Add unique timestamp suffix for model and synthetic dataset filenames
    timestamp = int(time.time())
    
    # Check MongoDB for existing model mapping
    mapping = model_mappings.find_one({"username": username, "filename": filename})
    if mapping and "model_path" in mapping and os.path.exists(mapping["model_path"]):
        model_path = mapping["model_path"]
        logging.info(f"📂 Loading existing CTGAN model for user {username} and file {filename}...")
        with open(model_path, 'rb') as f:
            ctgan = pickle.load(f)
    else:
        logging.info(f"🚀 Training new CTGAN model for user {username} and file {filename}...")
        ctgan = CTGAN(
            epochs=100,
            verbose=True,
            generator_lr=2e-4,
            discriminator_lr=1e-4,
            batch_size=500
        )
        if target_col:
            ctgan.fit(data_scaled, discrete_columns=[target_col])
        else:
            ctgan.fit(data_scaled)
        # Save model to unique path with timestamp
        safe_username = "".join(c for c in username if c.isalnum() or c in (' ','.','_')).rstrip()
        safe_filename = "".join(c for c in os.path.splitext(filename)[0] if c.isalnum() or c in (' ','.','_')).rstrip()
        model_path = os.path.join(output_dir, f"CTGAN_model_{safe_username}_{safe_filename}.pkl")
        with open(model_path, 'wb') as f:
            pickle.dump(ctgan, f)
        logging.info(f"✅ Model saved to {model_path}")
        # Update MongoDB mapping
        model_mappings.update_one(
            {"username": username, "filename": filename},
            {"$set": {"model_path": model_path}},
            upsert=True
        )

    logging.info("🎲 Generating synthetic samples...")
    synthetic_scaled = ctgan.sample(1000)

    common_cols = [col for col in data_scaled.columns if col in synthetic_scaled.columns]
    synthetic_scaled = synthetic_scaled[common_cols]

    synthetic_data = synthetic_scaled.copy()
    numeric_cols_filtered = [col for col in numeric_cols if col in synthetic_scaled.columns]
    synthetic_data[numeric_cols_filtered] = qt.inverse_transform(synthetic_scaled[numeric_cols_filtered])

    def quantile_map(syn_col, orig_col):
        sorted_orig = np.sort(orig_col)
        ranks = np.argsort(np.argsort(syn_col)) / (len(syn_col) - 1)
        return np.interp(ranks, np.linspace(0, 1, len(sorted_orig)), sorted_orig)

    for col in special_cols:
        if col in numeric_cols:
            synthetic_data[col] = quantile_map(synthetic_data[col].values, data[col].values)

    for col in numeric_cols:
        synthetic_data[col] = synthetic_data[col].clip(lower=data[col].min(), upper=data[col].max())

    data_rounded = data[numeric_cols].round(2)
    synthetic_data[numeric_cols] = synthetic_data[numeric_cols].round(2)

    safe_username = "".join(c for c in username if c.isalnum() or c in (' ','.','_')).rstrip()
    safe_filename = "".join(c for c in os.path.splitext(filename)[0] if c.isalnum() or c in (' ','.','_')).rstrip()
    save_path = os.path.join(output_dir, f"synthetic_{safe_username}_{safe_filename}_{timestamp}.csv")
    synthetic_data.to_csv(save_path, index=False)
    logging.info(f"✅ Saved: {save_path}")

    from app.gan import compare_datasets
    analysis_results = compare_datasets(data_rounded, synthetic_data, numeric_cols, special_cols, username, filename, output_dir, timestamp)

    # Add synthetic_csv_path key with relative filename for template use
    relative_path = os.path.relpath(save_path, start="app/static/Uploads").replace("\\", "/")
    analysis_results["synthetic_csv_path"] = relative_path

    return synthetic_data, analysis_results

def compare_datasets(original, synthetic, numeric_cols, special_cols, username=None, filename=None, output_dir="app/static/Uploads", timestamp=None):
    logging.info("🔍 Evaluating synthetic data quality...\n")
    print(f"✅ Original shape: {original.shape}, Synthetic shape: {synthetic.shape}")

    # Summary statistics
    print("\n📊 Mean and Std Dev Comparison")
    summary = original.describe().T.join(synthetic.describe().T, lsuffix="_orig", rsuffix="_synt")
    print(summary[["mean_orig", "mean_synt", "std_orig", "std_synt"]])

    # KS-Test
    print("\n🧪 Kolmogorov-Smirnov Test")
    ks_results = {
        col: ks_2samp(original[col], synthetic[col])
        for col in numeric_cols
    }
    ks_df = pd.DataFrame(ks_results).T
    ks_df.columns = ["KS Statistic", "P-Value"]
    print(ks_df.sort_values("KS Statistic", ascending=False))

    avg_ks = ks_df["KS Statistic"].mean()
    print(f"\n✅ Average KS Statistic: {avg_ks:.4f}")

    # Save summary and KS test as HTML tables for display
    summary_html = summary[["mean_orig", "mean_synt", "std_orig", "std_synt"]].to_html(classes="table table-striped", border=0)
    ks_html = ks_df.sort_values("KS Statistic", ascending=False).to_html(classes="table table-striped", border=0)

    # Create output directory for plots
    safe_username = "".join(c for c in username if c.isalnum() or c in (' ','.','_')).rstrip()
    safe_filename = "".join(c for c in os.path.splitext(filename)[0] if c.isalnum() or c in (' ','.','_')).rstrip()
    plot_dir = os.path.join(output_dir, f"{safe_username}_{safe_filename}_{timestamp}")
    os.makedirs(plot_dir, exist_ok=True)

    plot_paths = []

    # Correlation Plots
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    sns.heatmap(original.corr(), cmap="coolwarm", ax=axes[0], cbar=False)
    sns.heatmap(synthetic.corr(), cmap="coolwarm", ax=axes[1], cbar=False)
    axes[0].set_title("Original Correlation")
    axes[1].set_title("Synthetic Correlation")
    plt.tight_layout()
    corr_plot_path = os.path.join(plot_dir, f"correlation_{safe_username}_{safe_filename}.png")
    plt.savefig(corr_plot_path)
    plt.close()
    plot_paths.append(corr_plot_path)

    # Distribution comparison for special features
    for col in special_cols:
        if col in original.columns:
            plt.figure(figsize=(8, 4))
            sns.kdeplot(original[col], label="Original", color="blue")
            sns.kdeplot(synthetic[col], label="Synthetic", color="red")
            plt.title(f"Distribution: {col}")
            plt.legend()
            plt.tight_layout()
            dist_plot_path = os.path.join(plot_dir, f"distribution_{col}_{safe_username}_{safe_filename}.png")
            plt.savefig(dist_plot_path)
            plt.close()
            plot_paths.append(dist_plot_path)

    # PCA Visual Comparison
    pca = PCA(n_components=2)
    orig_pca = pca.fit_transform(original[numeric_cols])
    synth_pca = pca.transform(synthetic[numeric_cols])

    plt.figure(figsize=(8, 6))
    plt.scatter(orig_pca[:, 0], orig_pca[:, 1], alpha=0.5, label="Original", color="blue")
    plt.scatter(synth_pca[:, 0], synth_pca[:, 1], alpha=0.5, label="Synthetic", color="red")
    plt.title("PCA: Original vs. Synthetic")
    plt.xlabel("PC 1")
    plt.ylabel("PC 2")
    plt.legend()
    plt.tight_layout()
    pca_plot_path = os.path.join(plot_dir, f"pca_{safe_username}_{safe_filename}.png")
    plt.savefig(pca_plot_path)
    plt.close()
    plot_paths.append(pca_plot_path)

    # Interpretation text
    interpretation = f"""
    <h3>Interpretation of Results</h3>
    <p>The average Kolmogorov-Smirnov (KS) statistic is <strong>{avg_ks:.4f}</strong>, which indicates the overall similarity between the distributions of the original and synthetic datasets. Lower values suggest higher similarity.</p>
    <p>The correlation heatmaps show the relationships between features in both datasets. Similar patterns indicate that the synthetic data preserves the original data's structure.</p>
    <p>The distribution plots for special features compare the density estimates of these features, highlighting how well the synthetic data matches the original.</p>
    <p>The PCA plot visualizes the data in two principal components, showing the overlap and spread of the original and synthetic data points.</p>
    """

    # Convert plot paths to use forward slashes for URLs and make relative to app/static
    plot_paths = [os.path.relpath(path, start="app/static").replace("\\", "/") for path in plot_paths]

    # Debug log plot paths
    for p in plot_paths:
        print(f"Plot path: {p}")

    return {
        "summary_html": summary_html,
        "ks_html": ks_html,
        "plot_paths": plot_paths,
        "interpretation": interpretation
    }


