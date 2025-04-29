import torch
import torch.nn as nn
import torch.nn.functional as F
class Classifier(nn.Module):
    def __init__(self, feat_dim, nb_cls, cos_temp):
        super(Classifier, self).__init__()
        # 将 nn.Linear 作为子模块，bias=False 因为原始 apply_cosine 未使用 bias
        self.fc = nn.Linear(feat_dim, nb_cls, bias=False)
        self.cos_temp = cos_temp

    def forward(self, feature):
        # 对输入特征和权重进行归一化
        feature = F.normalize(feature, p=2, dim=1, eps=1e-12)
        weight = F.normalize(self.fc.weight.t(), p=2, dim=0, eps=1e-12)
        # 计算 cosine similarity
        cls_score = self.cos_temp * torch.mm(feature, weight)
        return cls_score