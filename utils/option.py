import argparse


def get_args_parser():
    parser = argparse.ArgumentParser(description='Failure prediction framework',
                                     add_help=True,
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--epochs', default=200, type=int, help='Total number of training epochs ')
    parser.add_argument('--batch-size', default=128, type=int, help='Batch size')
    parser.add_argument('--train-size', default=224, type=int, help='train size')
    
    ## optimizer
    parser.add_argument('--lr', default=0.1, type=float, help='Max learning rate for cosine learning rate scheduler')
    parser.add_argument('--weight-decay', default=5e-4, type=float, help='Weight decay')
    parser.add_argument('--momentum', default=0.9, type=float, help='Momentum')

    ## nb of run + print freq
    parser.add_argument('--nb-run', default=3, type=int, help='Run n times, in order to compute std')

    ## dataset setting
    parser.add_argument('--nb-worker', default=4, type=int, help='Nb of workers')
    parser.add_argument('--mixup-beta', default=10.0, type=float, help='beta used in the mixup data aug')

    ## Model + optim method + data aug + loss + post-hoc
    parser.add_argument('--model-name', default='resnet18', type=str,choices = ['resnet18', 'resnet32', 'resnet50', 'densenet', 'wrn', 'vgg', 'vgg19bn', 'deit', 'efficientnet_b3','efficientnet_b2'],
                        help='Models name to use')
    parser.add_argument('--resume-path', type=str, help='resume path')
    parser.add_argument('--deit-path', default = '/home/liyuting/lyt/deit_base_patch16_224-b5f2ef4d.pth', type=str, help='Official DeiT checkpoints')
    parser.add_argument('--optim-name', default='baseline', type=str, choices=['baseline', 'sam', 'swa', 'fmfp'],
                        help='Supported methods for optimization process')

    parser.add_argument('--save-dir', default='./output', type=str, help='Output directory')
    parser.add_argument('--resume', action='store_true', default=False, help='whether resume training')

    ## cosine classifier
    parser.add_argument('--use-cosine', action='store_true', default=False, help='whether use cosine classifier ')
    parser.add_argument('--cos-temp', type=int, default=8, help='temperature for scaling cosine similarity')

    ## fine-tuning
    parser.add_argument('--fine-tune-epochs', default=20, type=int, help='Total number of fine-tuning ')
    parser.add_argument('--fine-tune-lr', default=0.01, type=float,
                        help='Max learning rate for cosine learning rate scheduler')
    parser.add_argument('--reweighting-type', default=None, type=str, choices=['exp', 'threshold', 'power', 'linear'])
    parser.add_argument('--alpha', default=0.5, type=float, help='When you set re-weighting type to [threshold], you can set the threshold by changing alpha')
    parser.add_argument('--p', default=2, type=int, help='When you set re-weighting type to [power], you can set the power by changing p')
    parser.add_argument('--t', default=1.0, type=float, help='When you set re-weighting type to [exp], you can set the temperature by changing t')

    parser.add_argument('--crl-weight', default=0.0, type=float, help='CRL loss weight')
    parser.add_argument('--mixup-weight', default=0.0, type=float, help='Mixup loss weight')
    parser.add_argument('--gpu', default='9', type=str, help='GPU id to use')


    ## SWA parameters
    parser.add_argument('--swa-lr', default=0.05, type=float, help='swa learning rate')
    parser.add_argument('--swa-epoch-start', default=120, type=int, help='swa start epoch')

    ## dataset setting
    subparsers = parser.add_subparsers(title="dataset setting", dest="subcommand")

    # edit
    WSI = subparsers.add_parser(
        "WSI",
        description='Dataset parser for training on WSI',
        add_help=True,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        help="Dataset parser for training on TinyImgNet"
    )
    WSI.add_argument('--data-name', default='WSI', type=str, help='Dataset name')
    WSI.add_argument("--train-dir", type=str, default='/home/zyf/Projects/WSI/Datasets/WSI/train', help="WSI train directory")
    WSI.add_argument("--val-dir", type=str, default='/home/zyf/Projects/WSI/Datasets/WSI/val', help="WSI val directory")
    WSI.add_argument("--test-dir", type=str, default='/home/zyf/Projects/WSI/Datasets/WSI/test', help="WSI val directory")
    WSI.add_argument("--nb-cls", type=int, default=3, help="number of classes in WSI")
    WSI.add_argument("--imb-factor", type=float, default=1.0, help="imbalance rate in WSI") 

    return parser.parse_args()
