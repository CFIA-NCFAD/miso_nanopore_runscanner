import asyncio
import logging

import uvicorn

from miso_nanopore_runscanner.api import app as app_fastapi
from miso_nanopore_runscanner.config import HOST, PORT
from miso_nanopore_runscanner.tasks import app as app_rocketry

logger = logging.getLogger(__name__)


class Server(uvicorn.Server):
    """Customized uvicorn.Server

    Uvicorn server overrides signals and we need to include
    Rocketry to the signals."""

    def handle_exit(self, sig: int, frame) -> None:
        app_rocketry.session.shut_down(force=True)
        return super().handle_exit(sig, frame)


async def main():
    """Run scheduler and the API"""
    server = Server(
        config=uvicorn.Config(
            app_fastapi,
            host=HOST,
            port=PORT,
            workers=1,
            loop="asyncio"
        )
    )

    api = asyncio.create_task(server.serve())
    sched = asyncio.create_task(app_rocketry.serve())

    await asyncio.wait([sched, api])


def run():
    asyncio.run(main())


if __name__ == "__main__":
    asyncio.run(main())
