"""Offline classification comparison with a separate strict evidence sensitivity.

Never rewrites raw predictions, infers missing outputs, or calls a model.
"""
import argparse
import contextlib
import hashlib
import io
import json
from pathlib import Path

import pandas as pd
from compare_coverage import compare, INPUT_DIR, GOLD


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def report(b_dir, baseline_dir, output_dir, label_scheme='combined'):
    if output_dir.exists():
        raise ValueError('Choose a new analysis directory; preserve prior reports')
    protected = [Path(INPUT_DIR), Path(GOLD)]
    for folder in [b_dir, baseline_dir]:
        protected.extend(folder/name for name in ['nt_patient_llm_outputs.jsonl', 'calls.jsonl',
                                                  'run_manifest.json', 'prompt_snapshot.txt'] if (folder/name).exists())
    before = {str(p.resolve()): digest(p) for p in protected}
    output_dir.mkdir(parents=True)
    results = {}
    for name, policy in [('primary', 'classification'), ('strict_sensitivity', 'strict')]:
        with contextlib.redirect_stdout(io.StringIO()):
            results[name] = compare(b_dir, output_dir/name, label_scheme=label_scheme,
                                    baseline_dir=baseline_dir, evaluation_policy=policy)
        print(json.dumps({'analysis': name, 'policy': policy,
                          'eligible': {k: v['metric_denominator'] for k, v in results[name]['evaluations'].items()}}), flush=True)
    # Eligibility must be nested for each run, with paired comparisons using the
    # corresponding identical eligible-patient intersection under each policy.
    for run in results['primary']['evaluations']:
        sets = {}
        for analysis in results:
            table = pd.read_csv(output_dir/analysis/run/'NT_merged_results.csv', dtype={'BDSPPatientID': str})
            sets[analysis] = set(table.loc[table.metric_eligible, 'BDSPPatientID'])
        if not sets['strict_sensitivity'] <= sets['primary']:
            raise ValueError('Strict sensitivity cohort is not a subset of classification eligibility')
    if any(digest(path) != value for path, value in before.items()):
        raise ValueError('Original inference or reference artifact changed during analysis')
    source_files = [Path(__file__), Path(__file__).with_name('compare_coverage.py'),
                    Path(__file__).with_name('submission_tools.py'),
                    Path(__file__).parent/'NT_LLM/narcolepsy_analysis.py',
                    Path(__file__).parent/'NT_LLM/validation.py']
    policy = {'policy_version': 'classification-with-separate-quote-quality-v1',
              'label_scheme': label_scheme,
              'primary': 'All structurally valid predictions with valid study labels and matching patient/source metadata. Retain quote-only errors as evidence flags, not classification exclusions. Exclude all other recorded errors, missing/unusable predictions, and metadata mismatches.',
              'strict_sensitivity': 'Primary eligibility plus source quote verification using the same validation code and original notes for both v2 and v3.',
              'paired_metrics': 'Use identical eligible-patient intersection independently within each analysis policy.',
              'failure_handling': 'No missing predictions are imputed or converted to Uncertain. Raw run error fields remain unchanged and are exported separately.',
              'interpretation': 'Development-set diagnostic label classification performance, not clinical validation or a claim of fully source-grounded reasoning.',
              'analysis_code_sha256': {str(p.resolve()): digest(p) for p in source_files},
              'protected_artifacts_sha256': before,
              'original_artifacts_unchanged': True,
              'inference_rerun': False}
    (output_dir/'analysis_policy.json').write_text(json.dumps(policy, indent=2)+'\n')
    summary = {'policy': policy, 'analyses': results}
    (output_dir/'comparison.json').write_text(json.dumps(summary, indent=2)+'\n')
    lines = ['# Stanford v3 versus v2: classification and evidence quality', '',
             'Primary classification metrics include usable predictions carrying quote-quality flags. Evidence flags remain visible; no original output was rewritten.', '',
             '| Analysis | Run | Eligible / 128 | Accuracy | Balanced accuracy | Macro-F1 | Quote-flagged predictions included |',
             '| --- | --- | ---: | ---: | ---: | ---: | ---: |']
    for analysis, data in results.items():
        for name, evaluation in data['evaluations'].items():
            metrics = evaluation['metrics']
            display = (f'{metrics["accuracy"]:.2%} | {metrics["balanced_accuracy"]:.2%} | {metrics["macro_f1"]:.4f}'
                       if metrics else 'unavailable | unavailable | unavailable')
            lines.append(f'| {analysis} | {name} | {evaluation["metric_denominator"]} / {evaluation["gold_patients"]} | {display} | {evaluation["quote_flagged_predictions_in_metrics"]} |')
    lines += ['', '## Paired comparisons', '',
              'Compare these results on identical patients. Individual-run denominators above can differ.', '',
              '| Analysis | Comparison | Paired patients | v2 accuracy | v3 accuracy | v2 macro-F1 | v3 macro-F1 | Corrected | Regressed |',
              '| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for analysis, data in results.items():
        for name, groups in data['paired_comparisons'].items():
            paired = groups['all']
            if not paired['patients']: continue
            left = name.removesuffix('_vs_B'); a = paired['metrics'][left]; b = paired['metrics']['B']
            lines.append(f'| {analysis} | {name} | {paired["patients"]} | {a["accuracy"]:.2%} | {b["accuracy"]:.2%} | {a["macro_f1"]:.4f} | {b["macro_f1"]:.4f} | {paired["corrected"]} | {paired["regressed"]} |')
    lines += ['', '## Interpretation and retained records', '',
              '- Quote-quality failures do not establish patient ineligibility or an incorrect diagnostic label. They still require evidence review.',
              '- Strict sensitivity rechecks source quotes for both runs. Historical v2 recorded-error counts alone were not an equivalent quote-quality screen.',
              '- The full 128-patient denominator, technical failures, missing outputs and status counts remain in each reconciliation table. Accuracy uses eligible predictions; correct/128 is separately recorded as expected_record_accuracy.',
              '- Macro-F1 uses all four study labels; balanced accuracy averages recall over reference classes present. NT2 and IH map to NT2_IH in analysis copies only.',
              '- Review queues retain blank adjudication, confirmation and analysis-inclusion decisions. Metric eligibility is the stated computational policy, not clinical confirmation.',
              '- The raw recorded run error is retained alongside evaluation_status, metric_eligible and quote_quality_status. No inference or retries were performed.',
              '- The saved earlier strict-recorded comparison remains unchanged. This is a separately versioned analysis.', '',
              'See `primary/findings.md`, `strict_sensitivity/findings.md`, their confusion matrices and `consolidated_review.csv` files. `analysis_policy.json` records policy and artifact hashes.', '']
    (output_dir/'REPORT.md').write_text('\n'.join(lines))
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--B', type=Path, required=True)
    parser.add_argument('--baseline-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--label-scheme', choices=['five', 'combined'], default='combined')
    args = parser.parse_args()
    report(args.B, args.baseline_dir, args.output_dir, args.label_scheme)
