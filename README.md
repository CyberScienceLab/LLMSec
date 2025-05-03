# 🧠 Garak Dashboard for Adversarial Vulnerability Analysis

This repository contains an interactive Streamlit dashboard for analyzing the results of adversarial probes run using [Garak](https://docs.garak.ai/garak), an open-source tool for evaluating the robustness of large language models (LLMs).

---

## 📌 What is Garak?

[Garak](https://docs.garak.ai/garak) is an automated probing framework that identifies vulnerabilities in LLMs such as prompt injections, jailbreaks, safety violations, and more. It supports a variety of models and probes designed to simulate adversarial usage.

To learn more about Garak’s capabilities and probes, refer to their documentation:  
🔗 https://docs.garak.ai/garak

---

## 🛠 Project Overview

This project was implemented on a **Linux environment** using:

- Python 3
- [Streamlit](https://streamlit.io/) for dashboard development
- Garak for LLM adversarial testing

The dashboard provides an intuitive interface for visualizing Garak’s output and exploring detailed test results per probe, plugin, and run.

---

## 🚀 How to Use

### Step 1: Generate Summary from Garak Reports

Run the following command:

```bash
python3 garak_report_processor.py
```

This script processes Garak’s run reports and generates a summary JSON file that will be used by the dashboard.

> ⚠️ Make sure to modify the input and output paths in the script based on your own system setup.



### Step 2: Launch the Dashboard

Once the summary is generated, run:

```bash
streamlit run garak_dashboard_app.py
```

This will launch the interactive dashboard in your browser.

> ⚠️ Remember to update the necessary paths in the dashboard script to reflect your environment.


---

## 📊 Dashboard Features

The dashboard offers a clean and interactive way to explore Garak’s adversarial test results and run new scans.

### 🧩 Plugin-Based Summary

- The first page lists all plugins.
- Each plugin can be expanded to reveal the probes tested under it.
- For each probe, the dashboard displays:
  - Health score (pass rate)
  - Number of adversarial attempts
  - Failures per total test cases

### 🔎 Probe-Level Details

- Each probe has a checkbox to display deeper insights.
- When selected, users can view:
  - A trend chart showing pass/fail results over time
  - A date selector to filter specific run timestamps
  - A table showing failed prompts and their corresponding detectors

### 🎯 Run New Probes

- At the top of the page, users can select one or more probes (or entire plugins) to test.
- Selected probes can be launched directly via the dashboard.
- This triggers a fresh Garak scan using the configured model and environment.

---

## ⚠️ Limitations & Scalability Opportunities

While functional, the current dashboard version has several known limitations:

- ❌ It does **not handle disrupted Garak runs** (e.g., if a scan crashes midway)
- 🔧 Currently supports only:
  - `huggingface` as the model type
  - `gpt2` as the model name
- ⏳ Does not show **remaining time estimation** during probe execution
- 📊 Although **z-scores per detector** are already implemented in the backend, they are not yet exposed in the dashboard UI
- 🧪 Limited to what Garak exposes through its CLI and output formats

These are all areas we aim to improve in future versions for better fault-tolerance and user experience.

---


