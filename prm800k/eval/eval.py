import random
from collections import defaultdict
from typing import Dict, List
import blobfile as bf
import gzip
import orjson
import json
import numpy as np
import argparse
from typing import Any, Callable, Dict, List, Optional, Tuple
Sample = Dict[str, Any]

def json_loads(s: str) -> Dict:
    try:
        return orjson.loads(s)
    except Exception:
        return json.loads(s)  # fallback

def open_jsonl(file: str):
    if file.endswith(".gz"):
        return gzip.open(bf.BlobFile(file, "rb"))
    return bf.BlobFile(file, "r")

def _read_jsonl(file: str) -> List[Dict]:
    assert bf.exists(file), file
    with open_jsonl(file) as f:
        return [json_loads(l) for l in f.readlines() if l]

def _key_by_problem(samples: List[Dict]):
    grouped_samples = defaultdict(list)
    for sample in samples:
        grouped_samples[sample["problem"]].append(sample)
    return grouped_samples

def _get_answer(sample: Sample) -> Optional[str]:
    return sample.get("answer", sample.get("given_answer", None))

def _choose_sample_by_score(samples: List[Sample], key: str) -> Optional[Sample]:
    if len(samples) == 0:
        return None
    return max(samples, key=lambda x: x[key])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--method', type=str, default='prm') # one of ['orm', 'prm']
    args = parser.parse_args()
    method = args.method

    n_trials = 400
    samples_path = "az://openaipublic/process-supervision/scored-test-samples.jsonl"
    ns = [10, 25, 50, 75, 100, 200, 300, 400, 500, 750, 1000, 1250, 1500, 1860]
    all_trial_pass_rates = []
    num_samples_per_problem = 1860

    print(f"Reading {samples_path}, this may take a while...")
    samples = _read_jsonl(samples_path)
    print("Done.")
    samples_by_problem = _key_by_problem(samples)
    num_problems = len(samples_by_problem)

    for i in range(n_trials):
        pass_rates = []
        for n in ns:
            num_correct = 0
            for problem, problem_samples in samples_by_problem.items():
                nones = [None] * (num_samples_per_problem - len(problem_samples))
                problem_samples = problem_samples + nones
                random.shuffle(problem_samples)
                subsamples = list(problem_samples[:n])
                subsamples = [x for x in subsamples if x is not None]
                subsamples = [x for x in subsamples if _get_answer(x) is not None]

                if method == "prm":
                    choice = _choose_sample_by_score(subsamples, "prm_score")
                elif method == "orm":
                    choice = _choose_sample_by_score(subsamples, "orm_score")

                if choice is not None and choice["is_correct"]:
                    num_correct += 1
            pass_rates.append(num_correct / num_problems)
        all_trial_pass_rates.append(pass_rates)
        print(f"Trial {i}/{n_trials} {pass_rates}")

    all_trial_pass_rates = np.array(all_trial_pass_rates)
    print("Mean:", list(np.mean(all_trial_pass_rates, axis=0)))
    print("Standard deviation:", list(np.std(all_trial_pass_rates, axis=0)))

if __name__ == "__main__":
    main()
