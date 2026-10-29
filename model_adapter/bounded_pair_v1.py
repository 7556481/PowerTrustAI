"""Two existing official single-worker adapters, with physical-work leases."""
import asyncio


class BoundedPairAdapter:
    def __init__(self, first, second):
        self.children = (first, second)
        self._closed = False
        self.available = None
    @property
    def _active(self):
        return self
    def done(self):
        return all(getattr(c, '_active', None) is None or c._active.done() for c in self.children)
    def validate_request(self, request):
        self.children[0].validate_request(request)
    async def complete(self, request):
        from model_adapter.contracts import ModelConnectionError
        if self._closed:
            raise ModelConnectionError()
        if self.available is None:
            self.available = asyncio.Queue()
            for child in self.children:
                self.available.put_nowait(child)
        child = await self.available.get()
        loop = asyncio.get_running_loop()
        def release():
            if not self._closed:
                self.available.put_nowait(child)
        try:
            if self._closed:
                raise ModelConnectionError()
            return await child.complete(request)
        finally:
            active = getattr(child, '_active', None)
            if active is not None and not active.done():
                # Cancellation/timeout of shielded await does not free its HTTP lane.
                def finished(_):
                    if not loop.is_closed():
                        loop.call_soon_threadsafe(release)
                active.add_done_callback(finished)
            else:
                release()
    def close(self):
        self._closed = True
        try:
            self.children[0].close()
        finally:
            self.children[1].close()


def create_pair(settings, create):
    first = create(settings)
    try:
        second = create(settings)
    except BaseException:
        first.close()
        raise
    return BoundedPairAdapter(first, second)
