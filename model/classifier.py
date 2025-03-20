# edit
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


# import torch.nn 
# import torch.nn.functional as F
# import torch

# class Classifier(torch.nn.Module):
#     def __init__(self,
#                  feat_dim,
#                  nb_cls,
#                  cos_temp):
#         super(Classifier, self).__init__()

#         fc = torch.nn.Linear(feat_dim, nb_cls)        
#         self.weight = torch.nn.Parameter(fc.weight.t(), requires_grad=True)
#         self.bias = torch.nn.Parameter(fc.bias, requires_grad=True)
#         self.cos_temp = torch.nn.Parameter(torch.FloatTensor(1).fill_(cos_temp), requires_grad=False)
#         self.apply = self.apply_cosine
#     def get_weight(self):
#         return self.weight, self.bias

#     def apply_cosine(self, feature, weight, bias):
        
#         feature = F.normalize(feature, p=2, dim=1, eps=1e-12) ## Attention: normalized along 2nd dimension!!!
#         weight = F.normalize(weight, p=2, dim=0, eps=1e-12)## Attention: normalized along 1st dimension!!!

#         cls_score = self.cos_temp * (torch.mm(feature, weight))
#         return cls_score


#     def forward(self, feature):
#         weight, bias = self.get_weight()
#         cls_score = self.apply(feature, weight, bias)

#         return cls_score