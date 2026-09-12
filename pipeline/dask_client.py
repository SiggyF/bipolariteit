"""
Gedeelde dask-client-verbinding voor pipeline-stages die parallel werk
uitbesteden (tiling, LLM-batches). Verbindt bij voorkeur met de persistente
`dask scheduler`/`dask worker` die de devcontainer al opstart via
`postStartCommand` (zie .devcontainer/devcontainer.json), zodat meerdere
pipeline-stappen dezelfde "hoofdnode" delen i.p.v. elk hun eigen kortstondige
cluster op te tuigen.
"""

import logging

from dask.distributed import Client

logger = logging.getLogger(__name__)

# Vast adres, zodat de devcontainer-opstart (postStartCommand) al een `dask
# scheduler`/`dask worker` op deze poorten klaarzet -- pipeline-stages hoeven
# dan zelf geen cluster meer op te tuigen.
SCHEDULER_ADDRESS = "tcp://127.0.0.1:8786"


def make_client(dashboard: bool = True) -> Client | None:
    """Verbind bij voorkeur met een al draaiende `dask scheduler` (built-in
    dask-CLI, zie `dask --help` -- geen eigen wrapper eromheen). Geen
    scheduler bereikbaar (bv. buiten de devcontainer, of los uitgevoerd)? Val
    terug op een eigen, kortstondige lokale cluster -- zelfde dashboard-poort,
    maar verdwijnt met dit proces.
    """
    if not dashboard:
        return None
    try:
        client = Client(SCHEDULER_ADDRESS, timeout="2s")
        logger.info("Verbonden met bestaande dask-scheduler %s (dashboard: %s)", SCHEDULER_ADDRESS, client.dashboard_link)
        return client
    except OSError:
        client = Client(processes=False, dashboard_address=":8787")
        logger.info("Geen bestaande scheduler gevonden, eigen lokale cluster gestart (dashboard: %s)", client.dashboard_link)
        return client
