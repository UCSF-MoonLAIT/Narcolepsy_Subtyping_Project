from pathlib import Path
import argparse,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
parser=argparse.ArgumentParser(description='Generate three-way figures from aggregate data; no inference.')
selection=parser.add_mutually_exclusive_group();selection.add_argument('--review-dir',type=Path);selection.add_argument('--packet',type=Path,help='Compatibility with the earlier packet root')
parser.add_argument('--output-dir',type=Path)
args=parser.parse_args();p=((args.packet/'general') if args.packet else (args.review_dir or Path('review'))).resolve()
d=json.loads((p/'results/historical_A/comparison.json').read_text());dest=(args.output_dir or p/'figures').resolve();dest.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.titlesize':11,'pdf.fonttype':42})
short=['NT1','NT2/IH','Uncertain','Not NT/IH'];names={'historical_A':'Historical A','original_B':'Original B','combined_NT2_IH':'Combined NT2+IH'}
for policy,filename,heading in [('classification','figure_3_three_way_primary_confusion','Primary classification: three-way shared eligible patients'),('strict','figure_4_three_way_strict_confusion','Strict quote sensitivity: three-way shared eligible patients')]:
 fig,axes=plt.subplots(2,3,figsize=(15.5,10.6));fig.subplots_adjust(left=.10,right=.88,bottom=.18,top=.85,wspace=.62,hspace=.62);fig.suptitle(heading,fontsize=16,y=.97)
 for i,(cohort,ctitle) in enumerate([('all','Full cohort'),('beyond_cutoff_34','Beyond-cutoff subgroup')]):
  r=d['policies'][policy]['three_way_common'][cohort]
  for j,(name,title) in enumerate(names.items()):
   a=axes[i,j];m=np.array(r['metrics'][name]['confusion_matrix']);support=m.sum(axis=1);assert m.sum()==r['patients'];assert m.trace()==r['metrics'][name]['correct'];norm=np.divide(m,support[:,None],out=np.full(m.shape,np.nan),where=support[:,None]!=0)
   cm=plt.colormaps['Blues'].copy();cm.set_bad('#eeeeee');im=a.imshow(np.ma.masked_invalid(norm),vmin=0,vmax=1,cmap=cm)
   a.set_title(f'{chr(65+i*3+j)}  {title}\n{ctitle}, shared n = {r["patients"]}',pad=10);a.set_xticks(range(4),short,rotation=25,ha='right');a.set_yticks(range(4),[f'{s} (n={n})' for s,n in zip(short,support)]);a.set_xlabel('Predicted category');a.set_ylabel('Reference category' if j==0 else '')
   for x in range(4):
    for y in range(4):a.text(y,x,'—' if support[x]==0 else f'{m[x,y]}\n{norm[x,y]:.0%}',ha='center',va='center',fontsize=10,color='white' if support[x]>0 and norm[x,y]>.53 else '#202020')
   for spine in a.spines.values():spine.set_visible(False)
 cax=fig.add_axes([.92,.26,.014,.48]);cb=fig.colorbar(im,cax=cax);cb.ax.yaxis.set_major_formatter(PercentFormatter(1));cb.set_label('Percentage within reference category',labelpad=12)
 fig.text(.10,.065,'Historical A used a 7,000-character prefix and different runtime settings; comparisons are descriptive, not coverage-only effects.',fontsize=10)
 fig.text(.10,.035,'Cells show count and row percentage; gray rows have no reference cases. NT2/IH is grouped for all runs; Not NT/IH denotes neither disorder.',fontsize=10)
 for ext in ['png','pdf']:fig.savefig(dest/f'{filename}.{ext}',dpi=220,facecolor='white')
 plt.close(fig)
print('Generated and numerically reconciled the primary and strict three-way confusion figures.')
