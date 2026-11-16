import os
import time
import copy
import numpy as np

import torch
from torch import nn
import logging

from model import MainModel
from sklearn.metrics import ndcg_score

# How the epoch is chosen on the validation set. "HR@1" is the released criterion; its denominator (TP+FN) also counts
# correctly predicted normal chunks, so it drops when the model raises fewer false alarms. "combo" averages the standard
# F1 (penalises false alarms) and the standard HR@1 (localisation among faulty chunks).
SELECT_METRICS = {
    "HR@1": lambda r: r["HR@1"],
    "HR@1(std)": lambda r: r["HR@1(std)"],
    "F1(std)": lambda r: r["F1(std)"],
    "combo": lambda r: (r["F1(std)"] + r["HR@1(std)"]) / 2,
}

class BaseModel(nn.Module):
    def __init__(self, event_num, metric_num, node_num, device, lr=1e-3, epoches=50, patience=5, result_dir='./', hash_id=None, select_metric="combo", **kwargs):
        super(BaseModel, self).__init__()
        
        self.epoches = epoches
        self.lr = lr
        self.patience = patience # > 0: use early stop
        self.select_metric = select_metric
        assert select_metric in SELECT_METRICS, "select_metric must be one of {}".format(list(SELECT_METRICS))
        self.device = device

        self.model_save_dir = os.path.join(result_dir, hash_id)
        self.model = MainModel(event_num, metric_num, node_num, device, **kwargs)
        self.model.to(device)
    
    def evaluate(self, test_loader, datatype="Test"):
        self.model.eval()
        hrs, ndcgs = np.zeros(5), np.zeros(5)
        TP, FP, FN = 0, 0, 0
        n_faulty, tp_faulty = 0, 0 # for the "std" metrics below
        batch_cnt, epoch_loss = 0, 0.0
        
        with torch.no_grad():
            for graph, ground_truths in test_loader:
                res = self.model.forward(graph.to(self.device), ground_truths)
                for idx, faulty_nodes in enumerate(res["y_pred"]):
                    culprit = ground_truths[idx].item()
                    n_faulty += culprit != -1
                    if culprit == -1:
                        if faulty_nodes[0] == -1: TP+=1
                        else: FP += 1
                    else:
                        if faulty_nodes[0] == -1: FN+=1
                        else:
                            TP+=1
                            tp_faulty += 1
                            rank = list(faulty_nodes).index(culprit)
                            for j in range(5):
                                hrs[j] += int(rank <= j)
                                ndcgs[j] += ndcg_score([res["y_prob"][idx]], [res["pred_prob"][idx]], k=j+1)
                epoch_loss += res["loss"].item()
                batch_cnt += 1
        
        pos = TP+FN
        eval_results = {
                "F1": TP*2.0/(TP+FP+pos) if (TP+FP+pos)>0 else 0,
                "Rec": TP*1.0/pos if pos > 0 else 0,
                "Pre": TP*1.0/(TP+FP) if (TP+FP) > 0 else 0}
        
        for j in [1, 3, 5]:
            eval_results["HR@"+str(j)] = hrs[j-1]*1.0/pos
            eval_results["ndcg@"+str(j)] = ndcgs[j-1]*1.0/pos

        # Standard versions, added next to the released ones above. The released code counts correctly-predicted
        # normal chunks in TP, so its F1/Rec/Pre mix both classes and its HR@k/ndcg@k are divided by TP+FN
        # (faulty chunks + correct normal chunks). Here: the fault class only, and HR@k/ndcg@k over faulty chunks.
        # A missed fault (predicted normal) is a miss for HR@k and ndcg@k.
        fp_std, fn_std = FP, n_faulty - tp_faulty # normal chunks flagged as faulty, faulty chunks flagged as normal
        eval_results["F1(std)"] = 2.0*tp_faulty/(2*tp_faulty+fp_std+fn_std) if (2*tp_faulty+fp_std+fn_std) > 0 else 0
        eval_results["Rec(std)"] = tp_faulty*1.0/n_faulty if n_faulty > 0 else 0
        eval_results["Pre(std)"] = tp_faulty*1.0/(tp_faulty+fp_std) if (tp_faulty+fp_std) > 0 else 0
        for j in [1, 3, 5]:
            eval_results["HR@"+str(j)+"(std)"] = hrs[j-1]*1.0/n_faulty if n_faulty > 0 else 0
            eval_results["ndcg@"+str(j)+"(std)"] = ndcgs[j-1]*1.0/n_faulty if n_faulty > 0 else 0

        logging.info("{} -- {}".format(datatype, ", ".join([k+": "+str(f"{v:.4f}") for k, v in eval_results.items()])))

        return eval_results
    
    def fit(self, train_loader, val_loader, test_loader, evaluation_epoch=10):
        best_score, coverage, best_state, eval_res = -1, None, None, None # evaluation
        pre_loss, worse_count = float("inf"), 0 # early break

        def evaluate_epoch(epoch):
            # The epoch is selected on the validation set; the test set is only scored at the selected epoch.
            nonlocal best_score, coverage, best_state, eval_res
            val_results = self.evaluate(val_loader, datatype="Val")
            score = SELECT_METRICS[self.select_metric](val_results)
            if score > best_score:
                best_score, coverage = score, epoch
                eval_res = self.evaluate(test_loader, datatype="Test")
                eval_res["val_score"] = score
                eval_res["val_HR@1"] = val_results["HR@1"]
                best_state = copy.deepcopy(self.model.state_dict())
                self.save_model(best_state)

        optimizer = torch.optim.Adam(self.model.parameters(), lr=self.lr)
        #optimizer = torch.optim.SGD(self.model.parameters(), lr=self.lr, momentum=0.99)
        
        for epoch in range(1, self.epoches+1):
            self.model.train()
            batch_cnt, epoch_loss = 0, 0.0
            epoch_time_start = time.time()
            for graph, label in train_loader:
                optimizer.zero_grad()
                loss = self.model.forward(graph.to(self.device), label)['loss']
                loss.backward()
                # if self.debug:
                #     for name, parms in self.model.named_parameters():
                #         if name=='encoder.graph_model.net.weight':
                #             print(name, "--> grad:",parms.grad)
                optimizer.step()
                epoch_loss += loss.item()
                batch_cnt += 1
            epoch_time_elapsed = time.time() - epoch_time_start

            epoch_loss = epoch_loss / batch_cnt
            logging.info("Epoch {}/{}, training loss: {:.5f} [{:.2f}s]".format(epoch, self.epoches, epoch_loss, epoch_time_elapsed))

            ####### early break #######
            if epoch_loss > pre_loss:
                worse_count += 1
                if self.patience > 0 and worse_count >= self.patience:
                    logging.info("Early stop at epoch: {}".format(epoch))
                    break
            else: worse_count = 0
            pre_loss = epoch_loss

            ####### Evaluate during training #######
            if (epoch+1) % evaluation_epoch == 0:
                evaluate_epoch(epoch)

        if coverage is None: evaluate_epoch(epoch) # never evaluated (fewer epochs than evaluation_epoch)
        logging.info("* Best result got at epoch {} with validation {}: {:.4f}".format(coverage, self.select_metric, best_score))

        return eval_res, coverage
    
    def load_model(self, model_save_file=""):
        self.model.load_state_dict(torch.load(model_save_file, map_location=self.device))

    def save_model(self, state, file=None):
        if file is None: file = os.path.join(self.model_save_dir, "model.ckpt")
        try:
            torch.save(state, file, _use_new_zipfile_serialization=False)
        except:
            torch.save(state, file)
