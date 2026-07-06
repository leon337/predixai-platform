class BaseAdapter:
    """Base adapter stub. Never executes real orders in PTP-110."""

    name = "base"

    def __init__(self):
        self.connected = False

    def connect(self):
        self.connected = True

    def disconnect(self):
        self.connected = False

    def place_order(self, *args, **kwargs):
        raise RuntimeError("Real order execution is blocked in PTP-110")


class OlympTradeAdapter(BaseAdapter):
    name = "olymptrade"

    def place_order(self, *args, **kwargs):
        # Explicitly blocked: adapter exists but cannot send orders.
        raise RuntimeError("OlympTradeAdapter: executor blocked (PTP-110)")


class QuadcodeLikeAdapter(BaseAdapter):
    name = "quadcode_like"


class IQOptionAdapter(QuadcodeLikeAdapter):
    name = "iqoption"


class AvalonAdapter(QuadcodeLikeAdapter):
    name = "avalon"
