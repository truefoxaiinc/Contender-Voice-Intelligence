import json
import csv
from pathlib import Path
from src.config import TEST_CALLS_DIR, BASE_DIR
from src.llm_analyzer import analyze_transcript


def run_evaluation():
    test_files = list(TEST_CALLS_DIR.glob("*.json"))

    if not test_files:
        print(f"No test files found in {TEST_CALLS_DIR}. Please add sample call JSON files[cite: 1].")
        return

    results = []

    print(f"Starting evaluation on {len(test_files)} test calls...\n")

    for file_path in sorted(test_files):
        with open(file_path, "r", encoding="utf-8") as f:
            test_data = json.load(f)

        call_id = test_data.get("call_id", file_path.stem)
        transcript = test_data.get("transcript", "")
        expected_category = test_data.get("expected_category")
        expected_priority = test_data.get("expected_priority")

        print(f"Evaluating {call_id}...")

        # Call the main analysis pipeline[cite: 1]
        try:
            actual_output = analyze_transcript(call_id=call_id, transcript=transcript)

            act_cat = actual_output.get("category")
            act_prio = actual_output.get("priority")

            # Check match status
            cat_match = "PASS" if act_cat == expected_category else "FAIL"
            prio_match = "PASS" if act_prio == expected_priority else "FAIL"

            results.append({
                "Call ID": call_id,
                "Expected Category": expected_category,
                "Actual Category": act_cat,
                "Category Status": cat_match,
                "Expected Priority": expected_priority,
                "Actual Priority": act_prio,
                "Priority Status": prio_match,
                "Priority Reason": actual_output.get("priority_reason"),
                "Recommended Action": actual_output.get("recommended_next_action"),
                "Missing Info Detected": ", ".join(actual_output.get("missing_information", []))
            })
        except Exception as e:
            print(f"Error processing {call_id}: {e}")

    # Output to CSV for evaluation review[cite: 1]
    csv_out_path = BASE_DIR / "evaluation_results.csv"
    if results:
        fieldnames = results[0].keys()
        with open(csv_out_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)

        print(f"\nEvaluation completed! Results saved to: {csv_out_path}")


if __name__ == "__main__":
    run_evaluation()