
class Registry:

    vdp = None
    cfg = None

    @classmethod
    def init(cls, cfg, ctrl, vdp):
        Registry.cfg = cfg
        cls.ctrl = ctrl
        cls.vdp = vdp

