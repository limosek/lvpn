
class Registry:

    vdp = None
    cfg = None
    dbs = []

    @classmethod
    def init(cls, cfg, ctrl, vdp):
        Registry.cfg = cfg
        cls.ctrl = ctrl
        cls.vdp = vdp

