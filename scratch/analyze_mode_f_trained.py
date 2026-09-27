import json, csv, math
import numpy as np
from scipy import stats

with open('experiments/LITE_CODER_100TASK_MODE_A_BASELINE/checkpoint.json') as f:
    a_list = json.load(f)
    a_data = {t['task_id']: t for t in a_list}

with open('experiments/LITE_CODER_100TASK_MODE_D/checkpoint.json') as f:
    d_list = json.load(f)
    d_data = {t['task_id']: t for t in d_list}

with open('experiments/LITE_CODER_100TASK_MODE_F_TRAINED/checkpoint.json') as f:
    f_list = json.load(f)
    f_data = {t['task_id']: t for t in f_list}

with open('experiments/LITE_CODER_100TASK_MODE_F/checkpoint.json') as f:
    f_orig_list = json.load(f)
    f_orig_data = {t['task_id']: t for t in f_orig_list}

with open('data/benchmark/v1.0/dataset.json') as f:
    dataset = json.load(f)
    ds_map = {t['task_id']: t for t in dataset}

print("="*60)
print("1. METRIC CORRECTION")
print("="*60)
total_recorded_attempts = sum(t['attempts'] for t in f_list)
overall_recorded_mean = total_recorded_attempts / len(f_list)
succ_tasks = [t for t in f_list if t['success']]
failed_tasks = [t for t in f_list if not t['success']]
succ_attempts = [t['attempts'] for t in succ_tasks]
succ_mean = sum(succ_attempts) / len(succ_tasks)
failure_rate = len(failed_tasks) / len(f_list)

print(f"Total tasks: {len(f_list)}")
print(f"Successful tasks: {len(succ_tasks)}")
print(f"Failed tasks: {len(failed_tasks)}")
print(f"Failed tasks attempts: {[t['attempts'] for t in failed_tasks]}")
print(f"Total recorded attempts: {total_recorded_attempts}")
print(f"A. Overall recorded attempts mean: {overall_recorded_mean:.4f}")
print(f"B. Successful-task conditional attempts mean: {succ_mean:.4f}")
print(f"C. Failure rate: {failure_rate:.4f} ({failure_rate*100:.1f}%)")

print("\n" + "="*60)
print("2. TASK LEVEL COMPARISON CSV")
print("="*60)
rows = []
for t in f_list:
    tid = t['task_id']
    a_t = a_data.get(tid, {})
    d_t = d_data.get(tid, {})
    rows.append({
        'task_id': tid,
        'mode_a_success': a_t.get('success', False),
        'mode_d_success': d_t.get('success', False),
        'mode_f_success': t.get('success', False),
        'mode_a_attempts': a_t.get('attempts', 0),
        'mode_d_attempts': d_t.get('attempts', 0),
        'mode_f_attempts': t.get('attempts', 0),
        'mode_f_adapter_version': t.get('adapter_version', 'None'),
        'mode_f_active_adapter_id': t.get('active_adapter_id', 'None')
    })

with open('experiments/FINAL_LITE_CODER_EVIDENCE/task_level_comparison_trained.csv', 'w', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=[
        'task_id', 'mode_a_success', 'mode_d_success', 'mode_f_success',
        'mode_a_attempts', 'mode_d_attempts', 'mode_f_attempts',
        'mode_f_adapter_version', 'mode_f_active_adapter_id'
    ])
    writer.writeheader()
    writer.writerows(rows)
print("Wrote experiments/FINAL_LITE_CODER_EVIDENCE/task_level_comparison_trained.csv with 100 rows.")

print("\n" + "="*60)
print("3. SUCCESS-ONLY ATTEMPT & PAIRWISE ANALYSIS")
print("="*60)
# MODE-A: 100 successes, attempts mean
a_succ_att = [t['attempts'] for t in a_list if t['success']]
d_succ_att = [t['attempts'] for t in d_list if t['success']]
f_succ_att = [t['attempts'] for t in f_list if t['success']]

print(f"MODE-A: success={len(a_succ_att)}/100, all-mean={np.mean([t['attempts'] for t in a_list]):.4f}, succ-mean={np.mean(a_succ_att):.4f}")
print(f"MODE-D: success={len(d_succ_att)}/100, all-mean={np.mean([t['attempts'] for t in d_list]):.4f}, succ-mean={np.mean(d_succ_att):.4f}")
print(f"MODE-F Trained: success={len(f_succ_att)}/100, all-mean={overall_recorded_mean:.4f}, succ-mean={succ_mean:.4f}")

pairs = [
    ("MODE-A vs MODE-D", a_data, d_data, "MODE-A", "MODE-D"),
    ("MODE-A vs MODE-F Trained", a_data, f_data, "MODE-A", "MODE-F Trained"),
    ("MODE-D vs MODE-F Trained", d_data, f_data, "MODE-D", "MODE-F Trained"),
]

for name, dict1, dict2, l1, l2 in pairs:
    print(f"\n--- {name} ---")
    # 1. all-task recorded attempt difference (mean1 - mean2)
    att1_all = [dict1[tid]['attempts'] for tid in dict1]
    att2_all = [dict2[tid]['attempts'] for tid in dict1]
    all_diff = np.mean(att1_all) - np.mean(att2_all)
    print(f"1. All-task recorded attempt difference ({l1} - {l2}): {all_diff:.4f} (Note: {l2 if l2=='MODE-F Trained' else l1} zero-encoded failures distort this)")
    
    # 2. successful-task-only attempt difference
    succ1 = [dict1[tid]['attempts'] for tid in dict1 if dict1[tid]['success']]
    succ2 = [dict2[tid]['attempts'] for tid in dict2 if dict2[tid]['success']]
    succ_diff = np.mean(succ1) - np.mean(succ2)
    print(f"2. Successful-task-only attempt difference (overall) ({l1} - {l2}): {succ_diff:.4f}")
    
    # Also common successful tasks
    common_succ_tids = [tid for tid in dict1 if dict1[tid]['success'] and dict2[tid]['success']]
    common_succ_att1 = [dict1[tid]['attempts'] for tid in common_succ_tids]
    common_succ_att2 = [dict2[tid]['attempts'] for tid in common_succ_tids]
    paired_succ_diff = np.mean(common_succ_att1) - np.mean(common_succ_att2)
    print(f"   Common-successful tasks (n={len(common_succ_tids)}) paired mean difference: {paired_succ_diff:.4f}")
    
    # 3. success-rate difference
    sr1 = len(succ1) / len(dict1)
    sr2 = len(succ2) / len(dict2)
    print(f"3. Success-rate difference ({l1} - {l2}): {sr1 - sr2:.4f} ({sr1*100:.1f}% vs {sr2*100:.1f}%)")
    
    # 4. failure-rate difference
    fr1 = 1.0 - sr1
    fr2 = 1.0 - sr2
    print(f"4. Failure-rate difference ({l1} - {l2}): {fr1 - fr2:.4f} ({fr1*100:.1f}% vs {fr2*100:.1f}%)")

print("\n" + "="*60)
print("4. ADAPTER-SPECIFIC ANALYSIS")
print("="*60)
# Group MODE-F Trained tasks
groups = {
    'BASE MODEL': [],
    'adapter_v1': [],
    'adapter_v2': []
}

for t in f_list:
    aid = t.get('active_adapter_id')
    if aid is None:
        groups['BASE MODEL'].append(t)
    elif 'adapter_v1' in aid:
        groups['adapter_v1'].append(t)
    elif 'adapter_v2' in aid:
        groups['adapter_v2'].append(t)
    else:
        print("UNKNOWN ADAPTER:", aid)

adapter_perf_rows = []
for gname, tasks in groups.items():
    n_tasks = len(tasks)
    succ_t = [t for t in tasks if t['success']]
    fail_t = [t for t in tasks if not t['success']]
    sr = len(succ_t) / n_tasks if n_tasks > 0 else 0
    succ_atts = [t['attempts'] for t in succ_t]
    tot_succ_att = sum(succ_atts)
    mean_succ_att = np.mean(succ_atts) if succ_atts else 0
    median_succ_att = np.median(succ_atts) if succ_atts else 0
    print(f"\nGroup: {gname}")
    print(f"  Tasks: {n_tasks}")
    print(f"  Successful: {len(succ_t)}")
    print(f"  Failed: {len(fail_t)}")
    print(f"  Success rate: {sr:.4f} ({sr*100:.2f}%)")
    print(f"  Attempts on successful tasks: {tot_succ_att}")
    print(f"  Mean successful-task attempts: {mean_succ_att:.4f}")
    print(f"  Median successful-task attempts: {median_succ_att:.1f}")
    adapter_perf_rows.append({
        'group': gname,
        'number_of_tasks': n_tasks,
        'successful_tasks': len(succ_t),
        'failed_tasks': len(fail_t),
        'success_rate': f"{sr:.4f}",
        'attempts_on_successful_tasks': tot_succ_att,
        'mean_successful_task_attempts': f"{mean_succ_att:.4f}",
        'median_successful_task_attempts': f"{median_succ_att:.1f}"
    })

for out_path in ['adapter_performance.csv', 'experiments/FINAL_LITE_CODER_EVIDENCE/adapter_performance.csv']:
    with open(out_path, 'w', newline='') as f_out:
        writer = csv.DictWriter(f_out, fieldnames=[
            'group', 'number_of_tasks', 'successful_tasks', 'failed_tasks',
            'success_rate', 'attempts_on_successful_tasks',
            'mean_successful_task_attempts', 'median_successful_task_attempts'
        ])
        writer.writeheader()
        writer.writerows(adapter_perf_rows)
print("Saved adapter_performance.csv")

print("\n" + "="*60)
print("5. NEGATIVE-TRANSFER ANALYSIS")
print("="*60)
with open('experiments/LITE_CODER_100TASK_MODE_F_TRAINED/feedback.json') as f:
    fb_list = json.load(f)
    fb_map = {t['task_id']: t for t in fb_list}

print(f"Total failures in MODE-F Trained: {len(failed_tasks)}")
fail_records = []
for t in failed_tasks:
    tid = t['task_id']
    t_idx = t['task_index']
    ds_item = ds_map.get(tid, {})
    fb_item = fb_map.get(tid, {})
    fn_name = ds_item.get('function_name', 'unknown')
    aid = t.get('active_adapter_id')
    ver = t.get('adapter_version')
    att = t.get('attempts', 0)
    err_type = t.get('error_type')
    err_msg = t.get('error_message')
    status = t.get('status')
    # inspect generation failure reason from feedback
    gen_prompt = fb_item.get('generation_prompt', '')
    plan_in_prompt = 'PLAN:' in gen_prompt
    fail_records.append({
        'task_id': tid,
        'task_index': t_idx,
        'function_name': fn_name,
        'active_adapter_id': aid,
        'adapter_version': ver,
        'attempts': att,
        'status': status,
        'error_type': err_type,
        'error_message': err_msg,
        'plan_in_prompt': plan_in_prompt,
        'prompt_snippet': ds_item.get('prompt', '')[:50].replace('\n', ' ')
    })
    print(f"Task {t_idx} ({tid}) fn={fn_name} adapter={aid} status={status} att={att} plan_retrieved={plan_in_prompt}")

# Cluster analysis
fail_by_adapter = {}
for fr in fail_records:
    aid = fr['active_adapter_id']
    fail_by_adapter[aid] = fail_by_adapter.get(aid, 0) + 1
print("\nFailures by active adapter:", fail_by_adapter)

print("\n" + "="*60)
print("6. is_even ANALYSIS")
print("="*60)
is_even_tasks = []
for idx, ds_t in enumerate(dataset):
    tid = ds_t['task_id']
    prompt = ds_t.get('prompt', '')
    func = ds_t.get('function_name', '')
    if 'def is_even' in prompt or func == 'is_even':
        a_t = a_data[tid]
        d_t = d_data[tid]
        f_orig_t = f_orig_data[tid]
        f_t = f_data[tid]
        is_even_tasks.append({
            'task_index': idx + 1,
            'task_id': tid,
            'mode_a_success': a_t['success'],
            'mode_d_success': d_t['success'],
            'mode_f_orig_success': f_orig_t['success'],
            'mode_f_trained_success': f_t['success'],
            'mode_f_active_adapter_id': str(f_t.get('active_adapter_id')),
            'mode_f_adapter_version': str(f_t.get('adapter_version')),
            'mode_a_attempts': a_t['attempts'],
            'mode_d_attempts': d_t['attempts'],
            'mode_f_trained_attempts': f_t['attempts']
        })

print(f"Total is_even tasks identified: {len(is_even_tasks)}")
for row in is_even_tasks:
    print(f"Task {row['task_index']:03d} | {row['task_id']} | A:{row['mode_a_success']} | D:{row['mode_d_success']} | F_orig:{row['mode_f_orig_success']} | F_train:{row['mode_f_trained_success']} | adapter:{row['mode_f_active_adapter_id']}")

for out_path in ['is_even_adapter_analysis.csv', 'experiments/FINAL_LITE_CODER_EVIDENCE/is_even_adapter_analysis.csv']:
    with open(out_path, 'w', newline='') as f_out:
        writer = csv.DictWriter(f_out, fieldnames=[
            'task_index', 'task_id', 'mode_a_success', 'mode_d_success',
            'mode_f_orig_success', 'mode_f_trained_success',
            'mode_f_active_adapter_id', 'mode_f_adapter_version',
            'mode_a_attempts', 'mode_d_attempts', 'mode_f_trained_attempts'
        ])
        writer.writeheader()
        writer.writerows(is_even_tasks)
print("Saved is_even_adapter_analysis.csv")

print("\n" + "="*60)
print("7. TRAINING CYCLE ANALYSIS")
print("="*60)
with open('experiments/LITE_CODER_100TASK_MODE_F_TRAINED/training_history.json') as f:
    th = json.load(f)

for c in th:
    cid = c['training_cycle_id']
    aid = c['adapter_id']
    tt_id = c['trigger_task_id']
    tt_idx = c['trigger_task_index']
    n_ex = c['training_example_count']
    n_mem = c['source_memory_count']
    dur = c['duration_seconds']
    loss = c['training_loss']
    val = c['validation_status']
    prom = c['promotion_status']
    rel = c['reload_status']
    
    # tasks using adapter
    active_tasks = [t for t in f_list if t.get('active_adapter_id') == aid]
    n_act = len(active_tasks)
    succ_act = sum(1 for t in active_tasks if t['success'])
    fail_act = sum(1 for t in active_tasks if not t['success'])
    sr_act = succ_act / n_act if n_act > 0 else 0
    fr_act = fail_act / n_act if n_act > 0 else 0
    print(f"\nTraining Cycle: {cid}")
    print(f"  Adapter ID: {aid}")
    print(f"  Trigger task: Task {tt_idx} ({tt_id})")
    print(f"  Training examples: {n_ex} (from {n_mem} source memories)")
    print(f"  Duration: {dur:.2f}s")
    print(f"  Loss: {loss:.4f}")
    print(f"  Validation status: {val}")
    print(f"  Promotion status: {prom}")
    print(f"  Reload status: {rel}")
    print(f"  Tasks executed while active: {n_act}")
    print(f"  Success rate: {sr_act:.4f} ({succ_act}/{n_act})")
    print(f"  Failure rate: {fr_act:.4f} ({fail_act}/{n_act})")

print("\n" + "="*60)
print("8. STATISTICAL TESTS")
print("="*60)
# A. MODE-A vs MODE-D attempts (all successful, and common successful)
# Since both are 100/100 successful, all successful = common successful (n=100)
a_atts = np.array([a_data[t['task_id']]['attempts'] for t in f_list])
d_atts = np.array([d_data[t['task_id']]['attempts'] for t in f_list])
f_atts = np.array([t['attempts'] for t in f_list])
f_succ_mask = np.array([t['success'] for t in f_list])

# Test 1: MODE-A vs MODE-D (n=100)
diff_ad = a_atts - d_atts
t_ad, p_t_ad = stats.ttest_rel(a_atts, d_atts)
w_ad, p_w_ad = stats.wilcoxon(a_atts, d_atts)
mean_ad_diff = np.mean(diff_ad)
ci_ad = stats.t.interval(0.95, len(diff_ad)-1, loc=mean_ad_diff, scale=stats.sem(diff_ad))
cohen_d_ad = mean_ad_diff / np.std(diff_ad, ddof=1)
print(f"MODE-A vs MODE-D (Paired, n=100):")
print(f"  MODE-A mean: {np.mean(a_atts):.4f} (median: {np.median(a_atts)})")
print(f"  MODE-D mean: {np.mean(d_atts):.4f} (median: {np.median(d_atts)})")
print(f"  Mean difference: {mean_ad_diff:.4f}, 95% CI: [{ci_ad[0]:.4f}, {ci_ad[1]:.4f}]")
print(f"  Paired t-test: t={t_ad:.4f}, p={p_t_ad:.4e}")
print(f"  Wilcoxon signed-rank: W={w_ad:.4f}, p={p_w_ad:.4e}")
print(f"  Cohen's d: {cohen_d_ad:.4f}")

# Test 2: MODE-D vs MODE-F Trained: Common successful tasks only (n=92)
# Exclude the 8 tasks where MODE-F Trained failed
d_atts_common92 = d_atts[f_succ_mask]
f_atts_common92 = f_atts[f_succ_mask]
diff_df_92 = d_atts_common92 - f_atts_common92

t_df92, p_t_df92 = stats.ttest_rel(d_atts_common92, f_atts_common92)
# Check non-zero differences for Wilcoxon
diff_nz = diff_df_92[diff_df_92 != 0]
if len(diff_nz) > 0:
    w_df92, p_w_df92 = stats.wilcoxon(d_atts_common92, f_atts_common92)
else:
    w_df92, p_w_df92 = 0, 1.0
mean_df92_diff = np.mean(diff_df_92)
ci_df92 = stats.t.interval(0.95, len(diff_df_92)-1, loc=mean_df92_diff, scale=stats.sem(diff_df_92))
cohen_d_df92 = mean_df92_diff / np.std(diff_df_92, ddof=1) if np.std(diff_df_92, ddof=1) > 0 else 0

print(f"\nMODE-D vs MODE-F Trained (Common successful tasks only, n=92):")
print(f"  MODE-D mean (on these 92 tasks): {np.mean(d_atts_common92):.4f} (median: {np.median(d_atts_common92)})")
print(f"  MODE-F Trained mean (on these 92 tasks): {np.mean(f_atts_common92):.4f} (median: {np.median(f_atts_common92)})")
print(f"  Mean difference (D - F_trained): {mean_df92_diff:.4f}, 95% CI: [{ci_df92[0]:.4f}, {ci_df92[1]:.4f}]")
print(f"  Paired t-test: t={t_df92:.4f}, p={p_t_df92:.4e}")
print(f"  Wilcoxon signed-rank: W={w_df92:.4f}, p={p_w_df92:.4e}")
print(f"  Cohen's d: {cohen_d_df92:.4f}")

# Breakdown of attempt differences on these 92 common tasks:
diffs_count = {}
for d_val, f_val in zip(d_atts_common92, f_atts_common92):
    delta = d_val - f_val
    diffs_count[delta] = diffs_count.get(delta, 0) + 1
print(f"  Attempt difference distribution (D - F): {sorted(diffs_count.items())}")

# Test 3: MODE-A vs MODE-F Trained (Common successful tasks only, n=92)
a_atts_common92 = a_atts[f_succ_mask]
diff_af_92 = a_atts_common92 - f_atts_common92
t_af92, p_t_af92 = stats.ttest_rel(a_atts_common92, f_atts_common92)
w_af92, p_w_af92 = stats.wilcoxon(a_atts_common92, f_atts_common92)
mean_af92_diff = np.mean(diff_af_92)
ci_af92 = stats.t.interval(0.95, len(diff_af_92)-1, loc=mean_af92_diff, scale=stats.sem(diff_af_92))
cohen_d_af92 = mean_af92_diff / np.std(diff_af_92, ddof=1)
print(f"\nMODE-A vs MODE-F Trained (Common successful tasks only, n=92):")
print(f"  MODE-A mean (on these 92 tasks): {np.mean(a_atts_common92):.4f} (median: {np.median(a_atts_common92)})")
print(f"  MODE-F Trained mean (on these 92 tasks): {np.mean(f_atts_common92):.4f} (median: {np.median(f_atts_common92)})")
print(f"  Mean difference (A - F_trained): {mean_af92_diff:.4f}, 95% CI: [{ci_af92[0]:.4f}, {ci_af92[1]:.4f}]")
print(f"  Paired t-test: t={t_af92:.4f}, p={p_t_af92:.4e}")
print(f"  Wilcoxon signed-rank: W={w_af92:.4f}, p={p_w_af92:.4e}")
print(f"  Cohen's d: {cohen_d_af92:.4f}")

# Categorical analysis: McNemar's test for success/failure
# MODE-D vs MODE-F Trained:
# Contingency table (n=100):
# Both succ: 92
# D succ, F fail: 8
# D fail, F succ: 0
# Both fail: 0
# McNemar exact test: b=8, c=0
# Under null hypothesis b and c are Binomial(n=8, p=0.5)
# p-value = 2 * (0.5)^8 = 2 * (1/256) = 2/256 = 0.0078125
mcnemar_stat = 8  # or (abs(8-0)-1)**2 / (8+0) = 49/8 = 6.125 with continuity correction
p_mcnemar = stats.binom.pmf(8, 8, 0.5) + stats.binom.pmf(0, 8, 0.5)  # two-sided exact
print(f"\nMcNemar's test (MODE-D vs MODE-F Trained, n=100):")
print(f"  Contingency table: Both succ=92, D_succ/F_fail=8, D_fail/F_succ=0, Both fail=0")
print(f"  Exact two-sided binomial p-value: {p_mcnemar:.6f}")
print(f"  Asymptotic McNemar chi2 (with continuity correction): {((abs(8-0)-1)**2)/8:.4f}")
