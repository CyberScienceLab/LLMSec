import os
import json
from bs4 import BeautifulSoup

# --- Configuration ---
INPUT_DIR = "/home/sarina/.local/share/garak/garak_runs/"
OUTPUT_PATH = "/home/sarina/Desktop/garak_report_summary.json"

# --- Helper Functions ---

def parse_zscores(html_path):
    """Parse z-score values from the .report.html file."""
    zscore_lookup = {}
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as html_file:
            soup = BeautifulSoup(html_file, "html.parser")
            current_probe = None

            for tag in soup.find_all(["h3", "h4", "p"]):
                if tag.name == "h3" and "probe:" in tag.text:
                    current_probe = tag.text.split("probe:")[1].split()[0].strip()

                elif tag.name == "h4" and current_probe:
                    parts = tag.get_text().strip().split(" ")
                    if len(parts) >= 1:
                        detector_id = parts[0].strip()
                        zscore_tag = tag.find_next("p", class_="detector zscore")
                        if zscore_tag and "Z-score:" in zscore_tag.text:
                            z_val = zscore_tag.text.split("Z-score:")[-1].strip().replace(")", "").replace("(", "")
                            zscore_lookup[(current_probe, detector_id)] = z_val
    return zscore_lookup


def parse_failed_prompts(hitlog_path):
    """Parse failed prompts from the .hitlog.jsonl file."""
    failed_prompt_map = {}
    if os.path.exists(hitlog_path):
        with open(hitlog_path, "r") as f:
            for line in f:
                entry = json.loads(line)
                probe = entry.get("probe")
                detector = entry.get("detector")
                seq = entry.get("attempt_seq")
                prompt = entry.get("prompt")
                key = (probe, detector)
                if key not in failed_prompt_map:
                    failed_prompt_map[key] = []
                failed_prompt_map[key].append({"seq": seq, "prompt": prompt})
    return failed_prompt_map


def process_report(file_path, zscore_lookup, failed_prompt_map):
    """Process a single .report.jsonl file and return aggregated probe stats."""
    with open(file_path, "r") as f:
        lines = f.readlines()

    start_time = None
    end_time = None
    buffered_attempts = 0
    probe_buffer = {}
    all_attempts = []

    for line in lines:
        entry = json.loads(line)
        entry_type = entry.get("entry_type")

        if entry_type == "init":
            start_time = entry.get("start_time")

        elif entry_type == "attempt":
            buffered_attempts += 1
            all_attempts.append({
                "seq": entry.get("seq"),
                "status": entry.get("status"),
                "prompt": entry.get("prompt")
            })

        elif entry_type == "eval":
            probe_name = entry["probe"]
            detector_full = entry.get("detector", "")
            detector_name = detector_full.split("detector.")[-1] if "detector." in detector_full else detector_full
            passed = entry.get("passed", 0)
            total = entry.get("total", 0)

            if probe_name not in probe_buffer:
                probe_buffer[probe_name] = {
                    "passed": 0,
                    "total": 0,
                    "attempts": 0,
                    "detectors": [],
                    "prompts": all_attempts.copy()
                }

            z_score = zscore_lookup.get((probe_name, detector_name))
            failed_prompts = failed_prompt_map.get((probe_name, detector_name), [])

            probe_buffer[probe_name]["detectors"].append({
                "name": detector_name,
                "passed": passed,
                "total": total,
                "z_score": z_score,
                "failed_prompts": failed_prompts
            })

            probe_buffer[probe_name]["passed"] += passed
            probe_buffer[probe_name]["total"] += total
            probe_buffer[probe_name]["attempts"] += buffered_attempts

            buffered_attempts = 0
            all_attempts = []

        elif entry_type == "completion":
            end_time = entry.get("end_time")

    # Assign start and end time to each probe
    for probe_name, metrics in probe_buffer.items():
        metrics["start_time"] = start_time
        metrics["end_time"] = end_time

    return probe_buffer


# --- Main Execution ---

def main():
    combined_stats = {}

    for filename in os.listdir(INPUT_DIR):
        if filename.endswith(".report.jsonl"):
            file_path = os.path.join(INPUT_DIR, filename)
            base_filename = filename.replace(".report.jsonl", "")

            html_path = os.path.join(INPUT_DIR, base_filename + ".report.html")
            hitlog_path = os.path.join(INPUT_DIR, base_filename + ".hitlog.jsonl")

            # Parse z-scores and failed prompts
            zscore_lookup = parse_zscores(html_path)
            failed_prompt_map = parse_failed_prompts(hitlog_path)

            # Process report
            probe_buffer = process_report(file_path, zscore_lookup, failed_prompt_map)

            # Append to combined stats
            for probe_name, metrics in probe_buffer.items():
                if probe_name not in combined_stats:
                    combined_stats[probe_name] = []
                combined_stats[probe_name].append(metrics)

    # Save to output
    with open(OUTPUT_PATH, "w") as outfile:
        json.dump(combined_stats, outfile, indent=4)

    print(f"✅ Summary saved with full run history per probe to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
