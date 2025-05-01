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

    # Create a separate directory for plots inside output_dir
    plot_dir_name = f"{''.join(c for c in username if c.isalnum() or c in (' ','.','_')).rstrip()}_{''.join(c for c in os.path.splitext(filename)[0] if c.isalnum() or c in (' ','.','_')).rstrip()}_{timestamp}"
    plot_dir = os.path.join(output_dir, plot_dir_name)
    os.makedirs(plot_dir, exist_ok=True)

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
            epochs=1000,  # Increased epochs for better training
            verbose=True,
            generator_lr=1e-4,  # Reduced learning rate for generator
            discriminator_lr=5e-5,  # Reduced learning rate for discriminator
            batch_size=256,  # Reduced batch size for more stable training
            pac=1  # Set pac to 1 to avoid batch size assertion error
        )
        # Identify discrete columns more comprehensively
        discrete_columns = []
        if target_col:
            discrete_columns.append(target_col)
        # Add any other categorical columns if needed (example placeholder)
        # for col in data.columns:
        #     if data[col].dtype == 'object' and col != target_col:
        #         discrete_columns.append(col)
        if discrete_columns:
            ctgan.fit(data_scaled, discrete_columns=discrete_columns)
        else:
            ctgan.fit(data_scaled)
        # Save model to unique path without timestamp suffix
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
    save_path = os.path.join(plot_dir, f"synthetic_{safe_username}_{safe_filename}_{timestamp}.csv")
    synthetic_data.to_csv(save_path, index=False)
    logging.info(f"✅ Saved: {save_path}")

    from app.gan import compare_datasets
    analysis_results = compare_datasets(data_rounded, synthetic_data, plot_dir)

    # Add synthetic_csv_path key with relative filename for template use
    relative_path = os.path.relpath(save_path, start="app/static/Uploads").replace("\\", "/")
    analysis_results["synthetic_csv_path"] = relative_path

    return synthetic_data, analysis_results

import os
import pandas as pd

# Implement or import the plotting functions here
def save_correlation_plot(data, filepath):
    import matplotlib.pyplot as plt
    import seaborn as sns
    plt.figure(figsize=(10,8))
    corr = data.corr()
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm")
    plt.title("Correlation Matrix")
    plt.tight_layout()
    plt.savefig(filepath)
    plt.close()

def save_distribution_plot(original_data, synthetic_data, filepath):
    import matplotlib.pyplot as plt
    import seaborn as sns
    plt.figure(figsize=(12,8))
    numeric_cols = original_data.select_dtypes(include=['number']).columns
    for i, col in enumerate(numeric_cols):
        plt.subplot(len(numeric_cols)//3 + 1, 3, i+1)
        sns.kdeplot(original_data[col], label='Original', fill=True)
        sns.kdeplot(synthetic_data[col], label='Synthetic', fill=True)
        plt.title(col)
        plt.legend()
    plt.tight_layout()
    plt.savefig(filepath)
    plt.close()

def save_pca_plot(original_data, synthetic_data, filepath):
    import matplotlib.pyplot as plt
    from sklearn.decomposition import PCA
    import numpy as np
    pca = PCA(n_components=2)
    combined = pd.concat([original_data, synthetic_data])
    pca_result = pca.fit_transform(combined)
    plt.figure(figsize=(8,6))
    plt.scatter(pca_result[:len(original_data),0], pca_result[:len(original_data),1], label='Original', alpha=0.5)
    plt.scatter(pca_result[len(original_data):,0], pca_result[len(original_data):,1], label='Synthetic', alpha=0.5)
    plt.title("PCA Visualization")
    plt.legend()
    plt.savefig(filepath)
    plt.close()

def compare_datasets(original_data, synthetic_data, folder_path):
    import os
    import pandas as pd
    import numpy as np
    from scipy.stats import ks_2samp
    import matplotlib.pyplot as plt
    import seaborn as sns
    from sklearn.decomposition import PCA

    # Helpers for HTML
    def summary_html(orig_df, synth_df, features):
        orig_desc = orig_df[features].describe().round(2)
        synth_desc = synth_df[features].describe().round(2)
        # Select mean and std if present
        if all(stat in orig_desc.columns for stat in ["mean", "std"]) and all(stat in synth_desc.columns for stat in ["mean", "std"]):
            orig_desc = orig_desc[["mean", "std"]]
            synth_desc = synth_desc[["mean", "std"]]
            orig_desc.columns = ["Mean", "Std Dev"]
            synth_desc.columns = ["Mean", "Std Dev"]
        orig_html = orig_desc.to_html(classes="table table-striped table-bordered", border=0)
        synth_html = synth_desc.to_html(classes="table table-striped table-bordered", border=0)
        return orig_html, synth_html

    def ks_html(orig, synth):
        numeric = orig.select_dtypes(include="number").columns
        records = []
        for c in numeric:
            stat, p = ks_2samp(orig[c], synth[c])
            records.append((c, stat, p))
        ksdf = pd.DataFrame(records, columns=["Feature", "KS Stat", "P-Value"])
        ksdf.sort_values("KS Stat", ascending=False, inplace=True)
        top10 = ksdf.head(10).round(4)
        avg_ks_stat = ksdf["KS Stat"].mean()
        return top10.to_html(classes="table table-striped table-bordered", index=False, border=0), ksdf, avg_ks_stat

    # Determine top 6 features by KS statistic (dissimilarity) between original and synthetic
    ks_table_html, full_ks, avg_ks_stat = ks_html(original_data, synthetic_data)
    top6 = full_ks.sort_values("KS Stat", ascending=False).head(6)["Feature"].tolist()

    # 1) Summary & KS
    orig_summary_html, synth_summary_html = summary_html(original_data, synthetic_data, top6)

    plots = []

    # 2) Correlation of top6
    corr_path = os.path.join(folder_path, "corr_top6.png")
    plt.figure(figsize=(6, 5))
    # Calculate correlation on combined original and synthetic data for top6 features
    combined_corr_data = pd.concat([original_data[top6], synthetic_data[top6]], ignore_index=True)
    sns.heatmap(combined_corr_data.corr(), annot=True, fmt=".2f", cmap="coolwarm", cbar=False)
    plt.title("Correlation matrix of combined original and synthetic data (Top-6 Features)")
    plt.tight_layout(); plt.savefig(corr_path); plt.close()
    plots.append({
        "path": os.path.relpath(corr_path, os.path.join("app", "static")).replace("\\","/"),
        "caption": "Correlation matrix of combined original and synthetic data for the top 6 most dissimilar features."
    })

    # 3) Distribution overlays for top6
    dist_path = os.path.join(folder_path, "dist_top6.png")
    plt.figure(figsize=(12, 8))
    for i, col in enumerate(top6, 1):
        ax = plt.subplot(2, 3, i)
        sns.kdeplot(original_data[col], label="Orig", fill=True, alpha=0.4)
        sns.kdeplot(synthetic_data[col], label="Synth", fill=True, alpha=0.4)
        ax.set_title(col)
        ax.legend()
    plt.tight_layout(); plt.savefig(dist_path); plt.close()
    plots.append({
        "path": os.path.relpath(dist_path, os.path.join("app", "static")).replace("\\","/"),
        "caption": "Distribution overlays comparing original and synthetic data for the top 6 most dissimilar features."
    })

    # 4) PCA on top6
    pca_path = os.path.join(folder_path, "pca_top6.png")
    pca = PCA(n_components=2)
    combined = pd.concat([original_data[top6], synthetic_data[top6]], ignore_index=True)
    comps = pca.fit_transform(combined)
    n1 = len(original_data)
    plt.figure(figsize=(7,6))
    plt.scatter(comps[:n1,0], comps[:n1,1], alpha=0.5, label="Orig")
    plt.scatter(comps[n1:,0], comps[n1:,1], alpha=0.5, label="Synth")
    plt.title("PCA on Top-6 Features")
    plt.legend(); plt.tight_layout()
    plt.savefig(pca_path); plt.close()
    plots.append({
        "path": os.path.relpath(pca_path, os.path.join("app", "static")).replace("\\","/"),
        "caption": "2D PCA projection of original and synthetic data for the top 6 most dissimilar features."
    })

    # 5) Interpretation
    interp = (
        "<div style='font-family: Arial, sans-serif; font-size: 14px; line-height: 1.6;'>"
        "<p><strong>Feature Selection:</strong> The top 6 features were selected based on the highest dissimilarity (KS statistic) between the original and synthetic datasets, highlighting the most differing attributes.</p>"
        "<p><strong>Correlation Matrix:</strong> Calculated on the combined original and synthetic data for these features, this matrix reveals how well the synthetic data preserves the relationships present in the original data.</p>"
        "<p><strong>Distribution Overlays:</strong> These plots compare the distributions of each top feature, showing the degree of similarity between original and synthetic data.</p>"
        "<p><strong>PCA Projection:</strong> The 2D PCA plot visualizes the overall similarity in feature space, with overlapping clusters indicating good synthetic data quality.</p>"
        f"<p><strong>Average KS Statistic:</strong> {avg_ks_stat:.4f} (lower values indicate higher similarity between original and synthetic data)</p>"
        "</div>"
    )

    return {
        "orig_summary_html": orig_summary_html,
        "synth_summary_html": synth_summary_html,
        "ks_html": ks_table_html,
        "plot_infos": plots,
        "interpretation": interp,
        "average_ks_stat": avg_ks_stat
    }




