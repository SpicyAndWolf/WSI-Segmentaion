import torch
import valid
import os
import utils.test_option
import data.dataset
import data.CIFAR10C
import utils.utils
import model.get_model
from torch.optim.swa_utils import AveragedModel
import csv
from torch.utils.data import DataLoader
import torchvision.transforms

def process_results(loader, model, metrics, logger, method_name, results_storage):
    res = valid.validation(loader, model)
    for metric in metrics:
        results_storage[metric].append(res[metric])
    log = [f"{key}: {res[key]:.3f}" for key in res]
    logger.info(f'################## \n ---> Test {method_name} results：\t' + '\t'.join(log))

def test():

    os.environ['CUDA_VISIBLE_DEVICES'] = args.gpu
    metrics = ['Acc.', 'AUROC', 'AUPR Succ.', 'AUPR', 'FPR', 'AURC', 'EAURC', 'ECE', 'NLL', 'Brier']
    results_storage = {metric: [] for metric in metrics}
    cor_results_all_models = {}

    save_path = os.path.join(args.save_dir,
                             f"{args.data_name}_{args.model_name}_{args.optim_name}-mixup_{args.mixup_weight}-crl_{args.crl_weight}")
    logger = utils.utils.get_logger(save_path)

    for r in range(args.nb_run):
        logger.info(f'Testing model_{r + 1} ...')
        print(args)
        _, valid_loader, test_loader, nb_cls = data.dataset.get_loader(args.data_name, args.train_dir, args.val_dir,
                                                                       args.test_dir, args.batch_size, args.imb_factor, args.model_name)
        print(nb_cls)
        net = model.get_model.get_model(args.model_name, nb_cls, logger, args)

        # edit
        state_dict = torch.load(os.path.join(save_path, f'best_acc_net_{r + 1}.pth'))
        state_dict = {k.replace('module.', ''): v for k, v in state_dict.items()}
        net.load_state_dict(state_dict, strict=True)
        net = torch.nn.DataParallel(net).cuda()

        # if args.optim_name == 'fmfp' or args.optim_name == 'swa':
        #     net = AveragedModel(net)
        # net.load_state_dict(torch.load(os.path.join(save_path, f'best_acc_net_{r + 1}.pth')))
        # net = net.cuda()
        process_results(test_loader, net, metrics, logger, "MSP", results_storage)

    results = {metric: utils.utils.compute_statistics(results_storage[metric]) for metric in metrics}
    test_results_path = os.path.join(save_path, 'test_results.csv')
    utils.utils.csv_writter(test_results_path, args.data_name, args.model_name, metrics, results)

if __name__ == '__main__':
    args = utils.test_option.get_args_parser()
    test()

