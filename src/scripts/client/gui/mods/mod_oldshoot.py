from __future__ import absolute_import

import copy

import Keys
import SoundGroups
from CurrentVehicle import g_currentVehicle
from debug_utils import LOG_CURRENT_EXCEPTION, LOG_NOTE
from gui import InputHandler, SystemMessages
from items import vehicles

from gui.mods.oldshoot_data import VEHICLE_GUN_EVENTS


_PATCHED_VEHICLES = set()
_ORIGINAL_VEHICLE_TYPE_INIT = vehicles.VehicleType.__init__
_TEST_EVENT_INDEX = 0
_TEST_EVENTS = (
    'oldshoot_wpn_automatic_pc',
    'oldshoot_wpn_small_pc',
    'oldshoot_wpn_meduim_pc',
    'oldshoot_wpn_main_pc',
    'oldshoot_wpn_main_extra_pc',
    'oldshoot_wpn_large_pc',
    'oldshoot_wpn_large_extra_pc',
    'oldshoot_wpn_huge_pc',
    'oldshoot_wpn_main_dual_pc',
    'oldshoot_wpn_main_extra_dual_pc',
    'oldshoot_wpn_large_dual_pc',
    'oldshoot_wpn_automatic_npc',
    'oldshoot_wpn_small_npc',
    'oldshoot_wpn_meduim_npc',
    'oldshoot_wpn_main_npc',
    'oldshoot_wpn_main_extra_npc',
    'oldshoot_wpn_large_npc',
    'oldshoot_wpn_large_extra_npc',
    'oldshoot_wpn_huge_npc',
    'oldshoot_wpn_main_dual_npc',
    'oldshoot_wpn_main_extra_dual_npc',
    'oldshoot_wpn_large_dual_npc',
)


def _replace_shot_events(effects, player_event, npc_event):
    cloned_effects = copy.deepcopy(effects)
    for descriptor in cloned_effects.effectsList.descriptors():
        if getattr(descriptor, 'TYPE', None) == '_ShotSoundEffectDesc':
            descriptor._soundName = ((player_event,), (npc_event,))
    return cloned_effects


def _copy_gun(gun, events):
    cloned_gun = gun.copy()
    if isinstance(events, dict):
        effects = []
        for effect_name, player_event, npc_event in events['multi']:
            effect = vehicles.g_cache.gunEffects.get(effect_name)
            if effect is None:
                raise RuntimeError('Missing gun effect: %s' % effect_name)
            effects.append(_replace_shot_events(effect, player_event, npc_event) if player_event is not None else effect)
        cloned_gun.effects = effects
    else:
        cloned_gun.effects = _replace_shot_events(gun.effects, events[0], events[1])
    return cloned_gun


def _copy_turret(turret, configured_guns):
    changed = False
    guns = []
    for gun in turret.guns:
        events = configured_guns.get(gun.name)
        if events is None or not isinstance(events, dict) and gun.effects is None:
            guns.append(gun)
        else:
            guns.append(_copy_gun(gun, events))
            changed = True
    if not changed:
        return turret, False
    cloned_turret = turret.copy()
    cloned_turret.guns = tuple(guns)
    return cloned_turret, True


def _patch_vehicle(vehicle_type):
    identity = id(vehicle_type)
    if identity in _PATCHED_VEHICLES:
        return
    configured_turrets = VEHICLE_GUN_EVENTS.get(vehicle_type.name)
    if configured_turrets is None:
        return
    changed = False
    turret_groups = []
    for turret_group in vehicle_type.turrets:
        turrets = []
        for turret in turret_group:
            configured_guns = configured_turrets.get(turret.name, {})
            cloned_turret, turret_changed = _copy_turret(turret, configured_guns)
            turrets.append(cloned_turret)
            changed = changed or turret_changed
        turret_groups.append(tuple(turrets))
    if changed:
        vehicle_type.turrets = tuple(turret_groups)
        _PATCHED_VEHICLES.add(identity)


def _vehicle_type_init(self, *args, **kwargs):
    _ORIGINAL_VEHICLE_TYPE_INIT(self, *args, **kwargs)
    try:
        _patch_vehicle(self)
    except Exception:
        LOG_CURRENT_EXCEPTION()


def _on_test_key_down(event):
    global _TEST_EVENT_INDEX
    if event.key != Keys.KEY_F8 or not g_currentVehicle.isInHangar():
        return
    event_name = _TEST_EVENTS[_TEST_EVENT_INDEX]
    try:
        played = SoundGroups.g_instance.playSound2D(event_name)
        SystemMessages.pushMessage('[OldShootSounds] %s (%d/%d)' % (event_name, _TEST_EVENT_INDEX + 1, len(_TEST_EVENTS)), type=SystemMessages.SM_TYPE.Information)
        LOG_NOTE('[OldShootSounds] hangar test: %s, result: %r' % (event_name, played))
        _TEST_EVENT_INDEX = (_TEST_EVENT_INDEX + 1) % len(_TEST_EVENTS)
    except Exception:
        LOG_CURRENT_EXCEPTION()


def _install():
    vehicles.VehicleType.__init__ = _vehicle_type_init
    for vehicle_type in vehicles.g_cache.getVehicles():
        try:
            _patch_vehicle(vehicle_type)
        except Exception:
            LOG_CURRENT_EXCEPTION()
    InputHandler.g_instance.onKeyDown += _on_test_key_down
    LOG_NOTE('[OldShootSounds] whitelist loaded: %d vehicles' % len(VEHICLE_GUN_EVENTS))


_install()
