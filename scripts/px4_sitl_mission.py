"""Optional local PX4 SITL waypoint demo. No camera, obstacle, or dock integration.

Run only with an isolated simulated vehicle on UDP 14540; no hardware transport
is exposed by this script. The --execute flag enables simulated mission commands.
"""
import argparse
import asyncio
import json
import math
from pathlib import Path


def waypoint_coordinates(latitude, longitude, distance):
    if not all(math.isfinite(v) for v in (latitude, longitude, distance)) or not 0 < distance <= 20:
        raise ValueError('Finite coordinates and 0 < distance <= 20 meters required')
    if not -85 <= latitude <= 85 or not -180 <= longitude <= 180:
        raise ValueError('Demo requires nonpolar latitude and valid longitude')
    north_deg = distance / 111320.0
    return [(latitude, longitude), (latitude+north_deg, longitude), (latitude,longitude)]


def build_mission_items(route, altitude):
    from mavsdk.mission import MissionItem
    return [MissionItem(latitude_deg=lat,longitude_deg=lon,relative_altitude_m=altitude,
                  speed_m_s=2.0,is_fly_through=False,gimbal_pitch_deg=math.nan,gimbal_yaw_deg=math.nan,
                  camera_action=MissionItem.CameraAction.NONE,loiter_time_s=2.0,
                  camera_photo_interval_s=math.nan,acceptance_radius_m=2.0,yaw_deg=math.nan,
                  camera_photo_distance_m=math.nan,vehicle_action=MissionItem.VehicleAction.NONE)
           for lat,lon in route]



async def fly(distance, altitude, timeout, log_path):
    from mavsdk import System
    from mavsdk.mission import MissionPlan
    drone = System()
    await drone.connect(system_address='udp://:14540')
    events=[]
    log_path = Path(log_path)
    if log_path.exists():
        raise ValueError('Output log exists; choose another path')
    log_path.parent.mkdir(parents=True,exist_ok=True)
    armed=False
    def log(event, **details):
        row=dict(event=event,**details)
        events.append(row)
        log_path.write_text(json.dumps(events,indent=2))
        print(json.dumps(row),flush=True)

    async def mission():
        nonlocal armed
        async for state in drone.core.connection_state():
            if state.is_connected:
                break
        log('connected_local_sitl')
        async for health in drone.telemetry.health():
            if health.is_global_position_ok and health.is_home_position_ok:
                break
        async for position in drone.telemetry.position():
            route=waypoint_coordinates(position.latitude_deg,position.longitude_deg,distance)
            break
        items=build_mission_items(route, altitude)
        await drone.mission.set_return_to_launch_after_mission(True)
        await drone.mission.upload_mission(MissionPlan(items))
        await drone.action.arm()
        armed=True
        log('armed')
        await drone.mission.start_mission()
        async for progress in drone.mission.mission_progress():
            log('progress',current=progress.current,total=progress.total)
            if progress.total>0 and progress.current==progress.total:
                break
        # Verify return/landing through landed-state telemetry, not acknowledgement.
        from mavsdk.telemetry import LandedState
        async for state in drone.telemetry.landed_state():
            if state==LandedState.ON_GROUND:
                break
        async for state in drone.telemetry.armed():
            if not state:
                armed=False
                break
        log('returned_landed_disarmed')

    try:
        await asyncio.wait_for(mission(),timeout=timeout)
    except BaseException:
        log('failed_or_interrupted',armed=armed)
        if armed:
            try:
                await asyncio.wait_for(drone.action.return_to_launch(),timeout=10)
                log('return_requested_after_failure')
            except Exception as exc:
                log('return_request_failed',error=str(exc))
        raise


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute',action='store_true',help='Enable waypoint mission in isolated SITL')
    p.add_argument('--distance',type=float,default=10)
    p.add_argument('--altitude',type=float,default=10)
    p.add_argument('--timeout',type=float,default=180)
    p.add_argument('--output',type=Path,default=Path('outputs/sitl-events.json'))
    a=p.parse_args()
    if not a.execute:
        p.error('Use --execute only after starting isolated PX4 SITL; use sitl_telemetry.py for read-only checks')
    if not all(math.isfinite(v) for v in (a.distance,a.altitude,a.timeout)) or not 0<a.distance<=20 or not 2<=a.altitude<=20 or a.timeout<=0:
        p.error('Require distance (0,20], altitude [2,20] meters and finite positive timeout')
    asyncio.run(fly(a.distance,a.altitude,a.timeout,a.output))


if __name__=='__main__':
    main()
