import src.model.resnet50 as resnet50
import torchvision.models

def get_model(model_name, nb_cls, logger, args):
    if model_name == 'resnet50':
        net = resnet50.ResNet50(num_classes=nb_cls, use_cos=args.use_cosine, cos_temp=args.cos_temp).cuda()
        # 加载预训练权重
        pretrained_dict = torchvision.models.resnet50(pretrained=True).state_dict()
        net_dict = net.state_dict()
        pretrained_dict = {k: v for k, v in pretrained_dict.items() if k in net_dict and 'fc' not in k}
        net_dict.update(pretrained_dict)
        net.load_state_dict(net_dict, strict=False)
    msg = 'Using {} ...'.format(model_name)
    logger.info(msg)
    return net
