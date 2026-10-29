"""Opt-in citation-pair scheduling; unchanged schema13 messages and parsers."""
import asyncio
import json
from model_adapter.contracts import ModelOutputError
from model_adapter.runtime import current_budget

VERSION = 'schema13-citation-pair-v1'


class CorrectionOrder:
    """Earlier logical work owns the single correction, never fastest response."""
    def __init__(self, client, count):
        self.client = client
        self.done = [asyncio.Event() for _ in range(count)]
        self.used = False

    def for_item(self, index):
        order = self
        class Client:
            async def complete(self, messages, prompt_version, budget, correction=False, **kwargs):
                if correction:
                    for event in order.done[:index]:
                        await event.wait()
                    budget.raise_if_failed()
                    if order.used:
                        diagnostic = json.loads(messages[-1].content)['validation_error']
                        raise ModelOutputError(diagnostic)
                    order.used = True
                return await order.client.complete(messages, prompt_version, budget, correction, **kwargs)
        return Client()


async def waves(work, check, order):
    """First independent review is serial; later citation waves contain <=2 tasks."""
    async def perform(index):
        try:
            return await check(work[index], index)
        finally:
            order.done[index].set()
    first = await perform(0)
    yield [(work[0], first)]
    if first[2] or current_budget().fatal_error is not None:
        return
    start = 1
    while start < len(work):
        remaining = current_budget().limit - current_budget().used
        # With insufficient slack preserve canonical serial correction priority.
        width = 2 if remaining >= len(work) - start + (not order.used) else 1
        indexes = list(range(start, min(start + width, len(work))))
        tasks = [asyncio.create_task(perform(i)) for i in indexes]
        try:
            results = await asyncio.gather(*tasks)
        except BaseException:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise
        yield [(work[i], result) for i, result in zip(indexes, results)]
        if any(r[2] for r in results) or current_budget().fatal_error is not None:
            return
        if current_budget().used >= current_budget().limit:
            return
        start += width
