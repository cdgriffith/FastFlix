from dataclasses import dataclass


@dataclass
class Command:
    command: str
    variables: list
    internal: bool

@dataclass
class Loop:
    type: str
    condition: str


def generate_filters(**kwargs):
    """

    :param disable_hdr:
    :param scale_width:
    :param scale_height:
    :param crop:
    :param scale:
    :param scale_filter:
    :return:
    """
    crop = kwargs.get('crop')
    scale = kwargs.get('scale')
    scale_filter = kwargs.get('scale_filter', 'lanczos')
    scale_width = kwargs.get('scale_width')
    scale_height = kwargs.get('scale_height')
    disable_hdr = kwargs.get('disable_hdr')

    filter_list = []
    if crop:
        filter_list.append(f'crop={crop}')
    if scale:
        filter_list.append(f'scale={scale}:flags={scale_filter}')
    elif scale_width:
        filter_list.append(f'scale={scale_width}:-1:flags={scale_filter}')
    elif scale_height:
        filter_list.append(f'scale=-1:{scale_height}:flags={scale_filter}')

    if disable_hdr:
        filter_list.append('zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,'
                           'zscale=t=bt709:m=bt709:r=tv,format=yuv420p')

    return ",".join(filter_list)
