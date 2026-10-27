"""Read-only MAVSDK telemetry from local SITL. Does not arm or command a vehicle."""
import argparse
import asyncio
import json


async def sample(timeout):
    from mavsdk import System
    drone=System()
    await drone.connect(system_address='udp://:14540')
    async def collect():
        async for state in drone.core.connection_state():
            if state.is_connected:
                break
        async for position in drone.telemetry.position():
            print(json.dumps(dict(latitude=position.latitude_deg,longitude=position.longitude_deg,
                absolute_altitude_m=position.absolute_altitude_m,relative_altitude_m=position.relative_altitude_m)))
            return
    await asyncio.wait_for(collect(),timeout=timeout)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--timeout',type=float,default=30)
    a=p.parse_args()
    if a.timeout<=0:
        p.error('timeout must be positive')
    asyncio.run(sample(a.timeout))


if __name__=='__main__':
    main()
