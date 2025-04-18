# Governor functions

# TODO: rework it to use ophyd devices/components instead of epics.caget(...).

import epics
import time

def govMsgGet(configStr = 'Robot'):
    """
    Returns Governor message

    configStr: Governor configuration, 'Robot' or 'Human', default: 'Robot'
    
    Examples:
    govMsgGet()
    govMsgGet(configStr = 'Human')
    """
    blStr = blStrGet()
    if blStr == -1: return -1
    
    sysStr = 'XF:17IDC-ES:' + blStr
    devStr = '{Gov:' + configStr + '}'
    stsStr = 'Sts:Msg-Sts'
    pvStr = sysStr + devStr + stsStr
    govMsg = epics.caget(pvStr)
    
    return govMsg


def govStatusGet(stateStr, configStr = 'Robot'):
    """
    Returns the current active status for a Governor state
    
    configStr: Governor configuration, 'Robot', 'Human', 'Chip_Scanner' or 'Hepath'. default: 'Robot'
    stateStr: Governor short version state. Example: 'SA' for sample alignment
              one of ['M','SE','SA','TA','DA','XF','BL','BS','AB','CB','DI','CE','CA','CD','PA']

    Examples
    govStatusGet('SA')
    govStatusGet('SA', configStr = 'Human')
    """
    blStr = blStrGet()
    if blStr == -1: return -1
    
    if stateStr not in ['M','SE','SA','TA','DA','XF','BL','BS','AB','CB','DI','CE','CA','CD','PA']:
        print('stateStr must be one of: [M,SE,SA,TA,DA,XF,BL,BS,AB,CB,DI,CE,CA,CD,PA]')
        return -1
    
    sysStr = 'XF:17IDC-ES:' + blStr
    devStr = '{Gov:' + configStr + '-St:' + stateStr + '}'
    stsStr = 'Sts:Active-Sts'
    pvStr = sysStr + devStr + stsStr
    govStatus = epics.caget(pvStr)
    
    return govStatus


def govStateSet(stateStr, configStr = 'Robot'):
    """
    Sets Governor state

    configStr: Governor configuration, 'Robot', 'Human', 'Chip_Scanner' or 'Hepath'. default: 'Robot'
    stateStr: Governor short version state. Example: 'SA' for sample alignment
              one of ['M','SE','SA','TA','DA','XF','BL','BS','AB','CB','DI','CE','CA','CD','PA']

    Examples:
    govStateSet('SA')
    govStateSet('AB', configStr = 'Human')
    """
    blStr = blStrGet()
    if blStr == -1: return -1

    if stateStr not in ['M','SE','SA','TA','DA','XF','BL','BS','AB','CB','DI','CE','CA','CD','PA']:
        print('stateStr must be one of: M,SE,SA,TA,DA,XF,BL,BS,AB,CB,DI,CE,CA,CD,PA]')
        return -1
    
    sysStr = 'XF:17IDC-ES:' + blStr
    devStr = '{Gov:' + configStr + '}'
    cmdStr = 'Cmd:Go-Cmd'
    pvStr = sysStr + devStr + cmdStr
    epics.caput(pvStr, stateStr)
    
    while not govStatusGet(stateStr, configStr = configStr):
        print(govMsgGet(configStr = configStr))
        time.sleep(2)
    print(govMsgGet(configStr = configStr))
    
    return


def govPositionSet(position, positionerStr, positionTypeStr, configStr = 'Robot'):
    """
    Sets the Governor position for a positioner
    
    position: position value [motor units]
    positionerStr: Governor short version of positioner. Example: 'gy' for Gonio Y
    positionTypeStr: Type of position. Examples: 'Mount', 'Work', 'Park'
    configStr: Governor configuration, 'Robot' or 'Human', default: 'Robot'
    
    Example PV: XF:17IDC-ES:FMX{Gov:Robot-Dev:gy}Pos:Work-Pos
    
    Examples:
    govPositionSet(12913, 'gy', 'Work')
    govPositionSet(12913, 'gy', 'Work', configStr = 'Human')
    """
    blStr = blStrGet()
    if blStr == -1: return -1
    
    sysStr = 'XF:17IDC-ES:' + blStr
    devStr = '{Gov:' + configStr + '-Dev:' + positionerStr + '}'
    posStr = 'Pos:' + positionTypeStr + '-Pos'
    pvStr = sysStr + devStr + posStr
    epics.caput(pvStr, position)
    
    return


def govPositionGet(positionerStr, positionTypeStr, configStr = 'Robot'):
    """
    Returns the current Governor position for a positioner
    
    position: position value [motor units]
    positionerStr: Governor short version of positioner. Example: 'gy' for Gonio Y
    positionTypeStr: Type of position. Examples: 'Mount', 'Work', 'Park'
    configStr: Governor configuration, 'Robot' or 'Human', default: 'Robot'
    
    Example PV: XF:17IDC-ES:FMX{Gov:Robot-Dev:gy}Pos:Work-Pos
    
    Example: govPositionGet('gy', 'Work')
    Example: govPositionGet('gy', 'Mount', configStr = 'Human')
    """
    blStr = blStrGet()
    if blStr == -1: return -1
    
    sysStr = 'XF:17IDC-ES:' + blStr
    devStr = '{Gov:' + configStr + '-Dev:' + positionerStr + '}'
    posStr = 'Pos:' + positionTypeStr + '-Pos'
    pvStr = sysStr + devStr + posStr
    position = epics.caget(pvStr)
    
    return position


def govConfigSet(configStr):
    """
    Sets Governor Configuration

    configStr: Governor configuration, 'Robot', 'Human', 'Chip_Scanner', or 'Hepath'. default: 'Robot'
    
    Examples:
    govConfigSet('Chip_Scanner')
    """
    
    if configStr not in ['Robot','Human','Chip_Scanner','He_Path']:
        print('configStr must be one of: Robot,Human,Chip_Scanner,He_Path]')
        return -1
    
    blStr = blStrGet()
    if blStr == -1: return -1

    sysStr = 'XF:17IDC-ES:' + blStr
    devStr = '{Gov}'
    cmdStr = 'Config-Sel'
    pvStr = sysStr + devStr + cmdStr
    epics.caput(pvStr, configStr)
    
    return