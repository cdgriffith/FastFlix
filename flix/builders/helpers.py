# from dataclasses import dataclass
#
# @dataclass
# class Command:
#     command: str
#     variables: list
#     internal: bool
#
# @dataclass
# class Loop:
#     type: str
#     condition: str


class Loop:

    def __init__(self, type, condition):
        self.type = type
        self.condition = condition


class Command:

    def __init__(self, command, variables, internal):
        self.command = command
        self.variables = variables
        self.internal = internal


def generate_filters(**kwargs):
    """

    :param disable_hdr:
    :param scale_width:
    :param scale_height:
    :param crop:
    :param scale:
    :param scale_filter:
    :param rotate:
    :return:
    """
    crop = kwargs.get('crop')
    scale = kwargs.get('scale')
    scale_filter = kwargs.get('scale_filter', 'lanczos')
    scale_width = kwargs.get('scale_width')
    scale_height = kwargs.get('scale_height')
    disable_hdr = kwargs.get('disable_hdr')
    rotate = kwargs.get('rotate')
    vflip = kwargs.get('v_flip')
    hflip = kwargs.get('h_flip')

    filter_list = []
    if crop:
        filter_list.append(f'crop={crop}')
    if scale:
        filter_list.append(f'scale={scale}:flags={scale_filter}')
    elif scale_width:
        filter_list.append(f'scale={scale_width}:-1:flags={scale_filter}')
    elif scale_height:
        filter_list.append(f'scale=-1:{scale_height}:flags={scale_filter}')
    if rotate is not None:
        if rotate <= 3:
            filter_list.append(f'transpose={rotate}')
        if rotate == 4:
            filter_list.append(f'transpose=2,transpose=2')
    if vflip:
        filter_list.append('vflip')
    if hflip:
        filter_list.append('hflip')

    if disable_hdr:
        filter_list.append('zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,'
                           'zscale=t=bt709:m=bt709:r=tv,format=yuv420p')

    return ",".join(filter_list)
