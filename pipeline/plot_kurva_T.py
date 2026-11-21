#!/usr/bin/env python3
"""Grafik kurva T (F1 dan HR@1) dan biaya komputasi dari work/result/*/running.log.

Pakai (dari akar proyek):  work/envs/train312/bin/python -I pipeline/plot_kurva_T.py
Hasil: Report/Gambar_Kurva_T.png dan Report/Gambar_Biaya_T.png
Hanya run concat_glu 15 epoch untuk A1 (T=10), A1_T5/30/40/50. Nilai = baris Test terakhir di log (epoch terpilih),
sd memakai pembagi n-1. Sumbu y tidak dipotong dari nol pada grafik metrik (0,4 sampai 1,0).
"""
import json, glob, re, os, statistics as st
from datetime import datetime
rows=[]
for d in glob.glob("work/result/*/"):
    p=d+"params.json"; l=d+"running.log"
    if not (os.path.exists(p) and os.path.exists(l)): continue
    P=json.load(open(p)); txt=open(l).read().splitlines()
    if P.get("fusion")!="concat_glu" or P.get("epoches")!=15: continue
    data=P["data"]; 
    ep=[float(m.group(1)) for m in (re.search(r"training loss: [\d.]+ \[([\d.]+)s\]",x) for x in txt) if m]
    ts=[x[:19] for x in txt if x[:4]=="2026"]
    dur=(datetime.strptime(ts[-1],"%Y-%m-%d %H:%M:%S")-datetime.strptime(ts[0],"%Y-%m-%d %H:%M:%S")).total_seconds()
    best=[int(m.group(1)) for m in (re.search(r"Best result got at epoch (\d+)",x) for x in txt) if m]
    eff=[x for x in txt if "Efficiency" in x]
    e=re.search(r"params_total: (\d+).*infer_ms_per_window: ([\d.]+), peak_rss_mb: (\d+)",eff[-1]) if eff else None
    # last Test line before best-result line
    test=None
    for x in txt:
        if " Test -- " in x: test=x
    # test at chosen epoch: need epoch pairing; use Test lines in order, val-improvement logic -> take last Test line
    t={k:float(v) for k,v in re.findall(r"(\w+@?\d?\(std\)|F1\(std\)|Rec\(std\)|Pre\(std\)): ([\d.]+)",test)} if test else {}
    rows.append(dict(data=data,seed=P["random_seed"],h=os.path.basename(d.rstrip("/")),ep=st.mean(ep) if ep else None,dur=dur,best=best[-1] if best else None,
        params=int(e.group(1)) if e else None,ms=float(e.group(2)) if e else None,rss=int(e.group(3)) if e else None,
        F1=t.get("F1(std)"),Rec=t.get("Rec(std)"),Pre=t.get("Pre(std)"),HR1=t.get("HR@1(std)"),HR3=t.get("HR@3(std)"),HR5=t.get("HR@5(std)")))
rows.sort(key=lambda r:(r['data'],r['seed']))

import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
SURF,INK,INK2,GRID="#fcfcfb","#0b0b0b","#52514e","#e4e3df"
C1,C2="#2a78d6","#eb6834"
plt.rcParams.update({"font.family":"DejaVu Sans","text.color":INK,"axes.labelcolor":INK2,"xtick.color":INK2,"ytick.color":INK2})
def name(T,s): return ("A1" if T==10 else f"A1_T{T}")+"/"+s
def get(T,s,k): return [r[k] for r in rows if r["data"]==name(T,s)]
Ts={"within_event":[5,10,30,40,50],"leave_event_out":[10,30,40,50]}
title={"within_event":"within_event (event sama muncul di train dan test)","leave_event_out":"leave_event_out (event di test belum pernah dilihat)"}

fig,axs=plt.subplots(1,2,figsize=(11,4.6),sharey=True,facecolor=SURF)
for ax,s in zip(axs,Ts):
    ax.set_facecolor(SURF)
    for k,c,mk,lab,dx in [("F1",C1,"o","F1",-0.6),("HR1",C2,"s","HR@1",0.6)]:
        xs=Ts[s]; mean=[st.mean(get(T,s,k)) for T in xs]; sd=[st.stdev(get(T,s,k)) for T in xs]
        for T in xs:
            v=get(T,s,k); ax.scatter([T+dx]*len(v),v,s=14,color=c,alpha=.35,zorder=2,linewidths=0)
        ax.errorbar(xs,mean,yerr=sd,color=c,marker=mk,markersize=7,markeredgecolor=SURF,markeredgewidth=1.5,linewidth=2,capsize=3,elinewidth=1.2,zorder=3,label=lab)
        dy=7 if k=="HR1" else -7
        ax.annotate(f"{lab} {mean[-1]:.2f}",(xs[-1],mean[-1]),xytext=(11,dy),textcoords="offset points",va="center",fontsize=8.5,color=INK2)
        i10=xs.index(10)
        up = (k=="HR1") if s=="within_event" else True
        ax.annotate(f"{mean[i10]:.2f}",(10,mean[i10]),xytext=(0,20 if up else -22),textcoords="offset points",ha="center",va="center",fontsize=8.5,color=INK2,
                    bbox=dict(boxstyle="round,pad=0.15",fc=SURF,ec="none",alpha=.9))
    ax.set_title(title[s],fontsize=10.5,loc="left",color=INK)
    ax.set_xlabel("T (panjang jendela, detik)")
    ax.set_xticks(Ts["within_event"]); ax.set_xlim(2,62)
    ax.set_ylim(0.4,1.0); ax.grid(axis="y",color=GRID,linewidth=.8); ax.set_axisbelow(True)
    for sp in ["top","right","left"]: ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color(GRID); ax.tick_params(length=0)
axs[0].set_ylabel("Test, metrik std (rata-rata ± sd, 3 seed)")
axs[0].legend(loc="lower right",frameon=False,fontsize=9.5,labelcolor=INK2)
fig.suptitle("Efek panjang jendela T pada deteksi (F1) dan lokalisasi (HR@1), concat_glu",x=0.01,ha="left",fontsize=12.5,fontweight="bold",color=INK)
fig.text(0.01,0.005,"Titik pucat = tiap seed (42, 7, 123). Garis batang = ± sd (n−1). T = 5 hanya dijalankan di within_event. Angka di T = 10 dan T = 50 adalah rata-rata.",fontsize=8.5,color=INK2)
fig.tight_layout(rect=(0,0.03,1,0.95))
fig.savefig("Report/Gambar_Kurva_T.png",dpi=160,facecolor=SURF)

# biaya
fig,axs=plt.subplots(1,3,figsize=(11,3.6),facecolor=SURF)
spec=[("ep","Detik per epoch (rata-rata 15 epoch)"),("ms","Inferensi (ms per jendela)"),("rss","RAM puncak (GB)")]
for ax,(k,t) in zip(axs,spec):
    ax.set_facecolor(SURF)
    for s,c,mk,lab in [("within_event",C1,"o","within_event"),("leave_event_out",C2,"s","leave_event_out")]:
        xs=Ts[s]; ys=[st.mean(get(T,s,k))/(1000 if k=="rss" else 1) for T in xs]
        ax.plot(xs,ys,color=c,marker=mk,markersize=6,markeredgecolor=SURF,markeredgewidth=1.2,linewidth=2,label=lab)
        if k=="ms" and s=="within_event": continue
        ax.annotate(f"{ys[-1]:.1f}" if k!="ms" else f"{ys[-1]:.2f}",(xs[-1],ys[-1]),xytext=(7,0),textcoords="offset points",va="center",fontsize=8.5,color=INK2)
    ax.set_title(t,fontsize=10,loc="left",color=INK); ax.set_xlabel("T (detik)")
    ax.set_xticks(Ts["within_event"]); ax.set_xlim(2,60); ax.set_ylim(bottom=0)
    ax.grid(axis="y",color=GRID,linewidth=.8); ax.set_axisbelow(True)
    for sp in ["top","right","left"]: ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color(GRID); ax.tick_params(length=0)
axs[0].legend(loc="upper left",frameon=False,fontsize=9,labelcolor=INK2)
fig.suptitle("Biaya komputasi terhadap T: waktu latih dan RAM naik hampir linear, inferensi lebih tajam (CPU i7-8650U)",x=0.01,ha="left",fontsize=12,fontweight="bold",color=INK)
fig.tight_layout(rect=(0,0,1,0.93))
fig.savefig("Report/Gambar_Biaya_T.png",dpi=160,facecolor=SURF)
print("ok")
