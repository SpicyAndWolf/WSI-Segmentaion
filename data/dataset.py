import numpy as np
import torchvision.transforms
from torch.utils.data import DataLoader, Subset, Dataset
from torchvision.datasets import ImageFolder
from torch.utils.data.distributed import DistributedSampler


class CustomImageFolder(ImageFolder):
    def __init__(self, root, transform=None, target_transform=None, is_train=False, dataset_type='normal', imb_factor=None):
        super(CustomImageFolder, self).__init__(root, transform=transform, target_transform=target_transform)
        self.is_train = is_train

    def __getitem__(self, index):
        img, label = super(CustomImageFolder, self).__getitem__(index)
        return img, label, index


def TrainDataLoader(img_dir, transform_train, batch_size, is_train=True, dataset_type='normal', imb_factor=None):
    train_set = CustomImageFolder(img_dir, transform_train, is_train=is_train, dataset_type=dataset_type, imb_factor=imb_factor)
    train_loader = DataLoader(dataset=train_set, batch_size=batch_size, shuffle=True, num_workers=4, drop_last=True)
    return train_loader

# test data loader
def TestDataLoader(img_dir, transform_test, batch_size):
    test_set = CustomImageFolder(img_dir, transform_test)
    test_loader = DataLoader(dataset=test_set, batch_size=batch_size, shuffle=False, num_workers=4, drop_last=False)

    return test_loader

def get_loader(dataset, train_dir, val_dir, test_dir, batch_size, imb_factor, model_name):

    
    if dataset == "WSI":
        norm_mean, norm_std = (0.485, 0.456, 0.406), (0.229, 0.224, 0.225)
        nb_cls = 3

    # edit: 256,224 为Resnet的输入大小
    # edit: 320,300 为EfficientNet_b3的输入大小
    # edit: 280,260 为EfficientNet_b2的输入大小
    if dataset in ['WSI']:
        transform_train = torchvision.transforms.Compose([
                                                        torchvision.transforms.Resize(256),
                                                        torchvision.transforms.RandomResizedCrop(224),
                                                        torchvision.transforms.RandomHorizontalFlip(),
                                                        # torchvision.transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.1), # editSecond: 颜色增强
                                                        torchvision.transforms.ToTensor(),
                                                        torchvision.transforms.Normalize(norm_mean, norm_std)])
        transform_test = torchvision.transforms.Compose([
                                                        torchvision.transforms.Resize(256),
                                                        torchvision.transforms.CenterCrop(224),
                                                        torchvision.transforms.ToTensor(),
                                                        torchvision.transforms.Normalize(norm_mean, norm_std)])


    train_loader = TrainDataLoader(train_dir, transform_train, batch_size, is_train=True, dataset_type=dataset, imb_factor=imb_factor)
    val_loader = TestDataLoader(val_dir, transform_test, batch_size)
    test_loader = TestDataLoader(test_dir, transform_test, batch_size)

    return train_loader, val_loader, test_loader, nb_cls

