"""Measured Stanford-only runtime projection; update as completed calls accumulate."""
import argparse
import json
from pathlib import Path
from coverage_pipeline import ROOT, load_jsonl, atomic_json


def estimate(run_dir):
    plan=json.loads((ROOT/'NT_LLM/submission_20261109/token_coverage/summary.json').read_text())
    calls=load_jsonl(run_dir/'calls.jsonl');valid=[r for r in calls if r.get('raw_response',{}).get('prompt_eval_duration')]
    prompt_tokens=sum(r['raw_response'].get('prompt_eval_count') or 0 for r in valid)
    prompt_sec=sum((r['raw_response'].get('prompt_eval_duration') or 0)/1e9 for r in valid)
    output_tokens=sum(r['raw_response'].get('eval_count') or 0 for r in valid)
    output_sec=sum((r['raw_response'].get('eval_duration') or 0)/1e9 for r in valid)
    prompt_rate=prompt_tokens/prompt_sec if prompt_sec else None
    output_rate=output_tokens/output_sec if output_sec else None
    average_output=output_tokens/len(valid) if valid else None
    # Every multi-chunk patient needs at least one reduction. Large cases can need more.
    minimum_reductions=128-plan['B_direct_full_record_patients']
    minimum_calls=plan['B_total_source_calls']+minimum_reductions
    projection=(plan['B_source_prompt_tokens']/prompt_rate + minimum_calls*average_output/output_rate)/3600 if valid else None
    result={'target_cohort':'Stanford 128 only','completed_calls_measured':len(valid),
            'source_tokens':plan['total_source_tokens'],'planned_source_calls':plan['B_total_source_calls'],
            'minimum_reduction_calls':minimum_reductions,'minimum_total_calls':minimum_calls,
            'measured_prompt_tokens_per_second':prompt_rate,'measured_output_tokens_per_second':output_rate,
            'measured_mean_output_tokens':average_output,'projected_B_hours_before_reduction_input_and_retry_overhead':projection,
            'actual_completed_call_wall_hours':sum(r['elapsed_sec'] for r in calls)/3600,
            'limitations':'Provisional. Prompt cache, long-context speed, reduction input, hierarchy depth, retries, competing jobs, and clinical review change runtime. Includes all supplied source notes; never extrapolates to historical MGB.'}
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-dir',type=Path,required=True);p.add_argument('--output',type=Path)
    args=p.parse_args();value=estimate(args.run_dir)
    if args.output:atomic_json(args.output,value)
    print(json.dumps(value,indent=2))
