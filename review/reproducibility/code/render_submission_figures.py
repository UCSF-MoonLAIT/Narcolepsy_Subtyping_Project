"""Rebuild Figures 1–2 from aggregate paired matrices; no patient data or inference."""
from pathlib import Path
import argparse
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

parser = argparse.ArgumentParser(description=__doc__)
selection = parser.add_mutually_exclusive_group()
selection.add_argument('--review-dir', type=Path, help='Canonical aggregate review directory')
selection.add_argument('--packet', type=Path, help='Compatibility: earlier packet root containing general/')
parser.add_argument('--output-dir', type=Path, help='Figure destination; defaults to review/figures')
args = parser.parse_args()
review = ((args.packet / 'general') if args.packet else (args.review_dir or Path('review'))).resolve()
dest = (args.output_dir or review / 'figures').resolve()
dest.mkdir(parents=True, exist_ok=True)
matrices = json.loads((review / 'figures/paired_confusion_matrices.json').read_text())
labels = ['NT1', 'NT2_IH', 'Uncertain', 'Not_NT_IH']
display = ['NT1', 'NT2/IH', 'Uncertain', 'Not NT/IH']
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.titlesize': 11,
                     'axes.labelsize': 10, 'pdf.fonttype': 42, 'ps.fonttype': 42})
for policy, filename, heading in [
    ('primary', 'figure_1_primary_paired_confusion', 'Primary classification'),
    ('strict_sensitivity', 'figure_2_strict_paired_confusion', 'Strict source-quote sensitivity'),
]:
    saved = json.loads((review / f'results/{policy}/paired_comparisons.json').read_text())
    fig, axes = plt.subplots(2, 2, figsize=(11.4, 10.7))
    fig.subplots_adjust(left=.17, right=.86, bottom=.20, top=.87, wspace=.65, hspace=.80)
    fig.suptitle(heading + ' on identical eligible patients', fontsize=15, y=.97)
    for i, cohort in enumerate(['all', 'beyond_cutoff_34']):
        n = saved[cohort]['patients']
        for j, (key, title) in enumerate([
            ('original_pipeline_B', 'Original pipeline B'),
            ('combined_NT2_IH', 'Combined NT2+IH'),
        ]):
            record = matrices[policy][cohort][key]
            assert record['label_order'] == labels and record['patients'] == n
            matrix = np.array(record['confusion_matrix'])
            support = matrix.sum(axis=1)
            assert matrix.sum() == n
            metrics = saved[cohort]['metrics'][key]
            assert np.isclose(matrix.trace() / n, metrics['accuracy'])
            assert np.isclose(np.mean(np.diag(matrix)[support > 0] / support[support > 0]),
                              metrics['balanced_accuracy'])
            f1 = np.divide(2 * np.diag(matrix), support + matrix.sum(axis=0),
                           out=np.zeros(4), where=(support + matrix.sum(axis=0)) != 0)
            assert np.isclose(f1.mean(), metrics['macro_f1'])
            normalized = np.divide(matrix, support[:, None], out=np.full(matrix.shape, np.nan),
                                   where=support[:, None] != 0)
            ax = axes[i, j]
            cmap = plt.colormaps['Blues'].copy()
            cmap.set_bad('#eeeeee')
            im = ax.imshow(np.ma.masked_invalid(normalized), cmap=cmap, vmin=0, vmax=1)
            cname = 'Full cohort' if i == 0 else 'Beyond-cutoff subgroup'
            ax.set_title(f'{chr(65 + i * 2 + j)}  {title}\n{cname}, paired n = {n}', pad=10)
            ax.set_xticks(range(4), display, rotation=25, ha='right')
            ax.set_yticks(range(4), [f'{d} (n={count})' for d, count in zip(display, support)])
            ax.set_xlabel('Predicted category')
            ax.set_ylabel('Reference category' if j == 0 else '')
            for row in range(4):
                for col in range(4):
                    text = '—' if support[row] == 0 else f'{matrix[row, col]}\n{normalized[row, col]:.0%}'
                    color = 'white' if support[row] > 0 and normalized[row, col] > .53 else '#202020'
                    ax.text(col, row, text, ha='center', va='center', fontsize=10, color=color)
            for spine in ax.spines.values():
                spine.set_visible(False)
    cax = fig.add_axes([.91, .25, .017, .49])
    cb = fig.colorbar(im, cax=cax)
    cb.ax.yaxis.set_major_formatter(PercentFormatter(1))
    cb.set_label('Percentage within reference category', labelpad=12)
    fig.text(.17, .04, 'Cells show count and row percentage. Gray rows have no reference cases.\n'
             'NT2 and IH are grouped in both pipelines; Not NT/IH denotes Not_NT_IH (neither disorder).',
             fontsize=10)
    for extension in ['png', 'pdf']:
        fig.savefig(dest / f'{filename}.{extension}', dpi=220, facecolor='white')
    plt.close(fig)
print('Figures 1–2 generated from aggregate records; paired metrics reconcile. Tables unchanged.')
