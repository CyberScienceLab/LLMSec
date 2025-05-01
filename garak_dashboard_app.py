import streamlit as st
import json
import pandas as pd
import subprocess
import re
import matplotlib.pyplot as plt
from datetime import datetime
import collections
import time

# ========== Constants ==========
GARAK_PYTHON = "/home/sarina/garak-env/bin/python"  # ✅ Adjust if needed
SUMMARY_PATH = "/home/sarina/Desktop/garak_report_summary.json"
SUMMARY_SCRIPT = "/home/sarina/Desktop/LLMSec/garak_report_processor.py"

# ========== Utility Functions ==========
def load_summary(filepath):
    """Load JSON summary file."""
    with open(filepath, "r") as f:
        return json.load(f)

def parse_summary(data):
    """Parse Garak summary JSON into a clean DataFrame."""
    records = []
    for full_probe, runs in data.items():
        plugin, probe = full_probe.split(".", 1) if "." in full_probe else ("unknown", full_probe)
        for run in runs:
            passed = run["passed"]
            total = run["total"]
            health_score = passed / total if total > 0 else 0
            records.append({
                "Plugin": plugin,
                "Probe": probe,
                "Attempts": run["attempts"],
                "Failures": total - passed,
                "Health Score": round(health_score, 3),
                "Passed": passed,
                "Total": total,
                "Start Time": run.get("start_time"),
                "End Time": run.get("end_time")
            })
    df_raw = pd.DataFrame(records)
    df_grouped = df_raw.groupby(["Plugin", "Probe"]).agg({
        "Attempts": "sum",
        "Failures": "sum",
        "Passed": "sum",
        "Total": "sum",
        "Health Score": "mean"
    }).reset_index()
    return df_raw, df_grouped

def remove_ansi_codes(text):
    """Remove ANSI escape codes from text."""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

@st.cache_data
def get_available_probes():
    """Fetch available probes from Garak."""
    result = subprocess.run(
        [GARAK_PYTHON, "-m", "garak", "--list_probes"],
        capture_output=True, text=True
    )
    probes = []
    for line in result.stdout.splitlines()[1:]:
        cleaned = remove_ansi_codes(line)
        if cleaned.strip() and "SleepProbe" not in cleaned:
            probes.append(cleaned.split("–")[0].strip())
    return sorted(probes)

def run_garak(selected_probes):
    """Run Garak with selected probes and update summary."""
    cleaned_probes = [re.sub(r"[🌟💤]|^probes:\s*", "", p).strip() for p in selected_probes]
    probes_str = ",".join(cleaned_probes)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_prefix = f"dashboard_run_{timestamp}"

    command = (
        f"{GARAK_PYTHON} -m garak --model_type huggingface --model_name gpt2 "
        f"--probes {probes_str} --report_prefix {report_prefix} && "
        f"python3 {SUMMARY_SCRIPT}"
    )
    subprocess.run(["bash", "-c", command], check=True)
    

# ========== UI Rendering Functions ==========
def show_probe_summary(df, df_raw, data):
    """Display probes summary and detailed run insights."""
    st.write("📊 Summary of Garak probe results (all runs)")

    for plugin in df["Plugin"].unique():
        plugin_df = df[df["Plugin"] == plugin]
        expander_key = f"plugin_expander_{plugin}"

        # Dynamically update expander state before rendering
        if expander_key not in st.session_state:
            st.session_state[expander_key] = False

        # If any checkbox is selected for this plugin, open the expander
        for _, row in plugin_df.iterrows():
            checkbox_key = f"{plugin}_{row['Probe']}_showchart"
            if st.session_state.get(checkbox_key, False):
                st.session_state[expander_key] = True
                break

        with st.expander(f"🧩 Plugin: {plugin}", expanded=st.session_state[expander_key]):
            for _, row in plugin_df.iterrows():
                render_probe_details(plugin, row, df_raw, data)


def render_probe_details(plugin, row, df_raw, data):
    """Render details for a specific probe."""
    st.subheader(f"🔹 Probe: {row['Probe']}")
    col1, col2, col3 = st.columns(3)
    col1.metric("Adversarial Attempts", row["Attempts"])
    col2.metric("Failed Tests", f"{row['Failures']}/{row['Total']}")
    col3.metric("Health Score", f"{row['Health Score']*100:.1f}%")

    checkbox_key = f"{plugin}_{row['Probe']}_showchart"
    show_chart = st.checkbox(f"📊 Show detailed insights for {row['Probe']}", key=checkbox_key)

    if show_chart:
        show_probe_chart(plugin, row['Probe'], df_raw)
        show_run_details(plugin, row['Probe'], data)

def show_probe_chart(plugin, probe, df_raw):
    """Plot bar chart for passed/failed test cases."""
    run_history = df_raw[(df_raw["Plugin"] == plugin) & (df_raw["Probe"] == probe)].copy()
    if len(run_history) > 1:
        run_history["Timestamp"] = pd.to_datetime(run_history["Start Time"])
        run_history = run_history.sort_values("Timestamp")
        run_history["Label"] = run_history["Timestamp"].dt.strftime("%b %d – %H:%M")
        run_history["Failures"] = run_history["Total"] - run_history["Passed"]

        labels = run_history["Label"]
        passed = run_history["Passed"]
        failed = run_history["Failures"]

        fig, ax = plt.subplots(figsize=(6, 0.5 * len(labels)))
        ax.barh(labels, passed, color="#66bb6a", label="Passed")
        ax.barh(labels, failed, left=passed, color="#ef5350", label="Failed")

        ax.set_xlabel("Total Tests")
        ax.set_ylabel("Run Time")
        ax.invert_yaxis()
        ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.05), ncol=2, frameon=False, fontsize=10)
        ax.tick_params(axis='y', labelsize=9)

        for i, (p, f) in enumerate(zip(passed, failed)):
            if p > 0:
                ax.text(p / 2, i, str(p), va="center", ha="center", color="white", fontsize=9)
            if f > 0:
                ax.text(p + f / 2, i, str(f), va="center", ha="center", color="white", fontsize=9)

        left, center, right = st.columns([0.15, 5.5, 1])
        with center:
            st.pyplot(fig, bbox_inches='tight')
    else:
        st.info("📌 Only one run available — trend chart skipped.")

def show_run_details(plugin, probe, data):
    """Display run details including prompts and detector failures."""
    full_probe = f"{plugin}.{probe}"
    run_entries = data.get(full_probe, [])

    run_df = pd.DataFrame(run_entries)
    run_df["Timestamp"] = pd.to_datetime(run_df["start_time"])
    run_df = run_df.sort_values("Timestamp")
    run_df["Label"] = run_df["Timestamp"].dt.strftime("%b %d – %H:%M")

    st.markdown("##### 📅 Run Details")
    selected_labels = st.multiselect(
        f"Select run time(s) for {probe}:",
        options=run_df["Label"].tolist()
    )

    for label in selected_labels:
        run = run_df[run_df["Label"] == label].iloc[0]
        st.markdown(f"**🕒 Run at {label}**")
        
        prompts = run.get("prompts", [])
        if prompts:
            df_prompts = pd.DataFrame(prompts)[["seq", "status", "prompt"]]
            st.markdown("**💬 Prompts used in this run**")
            st.dataframe(df_prompts)
        else:
            st.info("No prompts available.")

        if "detectors" in run:
            table_data = []
            for detector in run["detectors"]:
                name = detector.get("name")
                fails = detector.get("failed_prompts", [])
                counter = collections.Counter(f["prompt"] for f in fails)
                
                if not counter:
                    table_data.append({"Detector": name, "Prompt": "—", "Fails": 0})
                else:
                    for prompt, count in counter.items():
                        table_data.append({"Detector": name, "Prompt": prompt, "Fails": count})

            df_details = pd.DataFrame(table_data)
            st.markdown("**📋 Detector Failures**")
            st.dataframe(df_details, use_container_width=True)
        else:
            st.info("No detector data available.")

# ========== Main App ==========
st.title("Invisible Hands Dashboard")

# Load and parse
data = load_summary(SUMMARY_PATH)
df_raw, df = parse_summary(data)

# Garak Run Section
st.title("🧪 Run Garak Scan")
available_probes = get_available_probes()
selected_probes = st.multiselect("Select probes to run:", available_probes)

if st.button("🚀 Run Selected Probes") and selected_probes:
    with st.spinner("Running Garak and updating summary..."):
        run_garak(selected_probes)

    # After running Garak, reload the updated summary
    data = load_summary(SUMMARY_PATH)
    df_raw, df = parse_summary(data)

    st.success("✅ Garak run completed and dashboard updated!")


# Show Probe Summaries
show_probe_summary(df, df_raw, data)

# Optional Footer
st.caption("Developed by CyberScience Lab 🚀")
