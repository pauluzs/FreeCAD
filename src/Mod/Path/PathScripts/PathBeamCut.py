# -*- coding: utf-8 -*-

# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2018 sliptonic <shopinthewoods@gmail.com>               *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2 of     *
# *   the License, or (at your option) any later version.                   *
# *   for detail see the LICENCE text file.                                 *
# *                                                                         *
# *   This program is distributed in the hope that it will be useful,       *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU Library General Public License for more details.                  *
# *                                                                         *
# *   You should have received a copy of the GNU Library General Public     *
# *   License along with this program; if not, write to the Free Software   *
# *   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
# *   USA                                                                   *
# *                                                                         *
# ***************************************************************************

import FreeCAD
import Part
import Path
import PathScripts.PathEngraveBase as PathEngraveBase
import PathScripts.PathLog as PathLog
import PathScripts.PathOp as PathOp
import PathScripts.PathOpTools as PathOpTools
import PathScripts.PathUtil as PathUtil
import math

from PySide import QtCore

if False:
    PathLog.setLevel(PathLog.Level.DEBUG, PathLog.thisModule())
    PathLog.trackModule(PathLog.thisModule())
else:
    PathLog.setLevel(PathLog.Level.INFO, PathLog.thisModule())

# Qt tanslation handling
def translate(context, text, disambig=None):
    return QtCore.QCoreApplication.translate(context, text, disambig)

def toolOffset(ToolComp, width, Depth, tool):
    '''toolOffset(ToolComp, width, Depth, tool) ... return tuple for given parameters.'''
    depth = 0 # Fixed at 0, tool never goes into work
    toolOffset = tool.Diameter/2
    extraOffset =  width - ((tool.Diameter/2)*(not ToolComp))
    if extraOffset <= -(tool.Diameter/2):# We need to stay on the correct side
	extraOffset = -(tool.Diameter/2) + 0.00001 #Offset to correct side by smallest unit(faster than offsetting twice)
    offset = toolOffset + extraOffset
    return (depth, offset)

class ObjectBeamCut(PathEngraveBase.ObjectOp):
    '''Proxy class for BeamCut operation.'''

    def opFeatures(self, obj):
        return PathOp.FeatureTool | PathOp.FeatureHeights | PathOp.FeatureStepDown | PathOp.FeatureBaseEdges | PathOp.FeatureBaseFaces

    def initOperation(self, obj):
        PathLog.track(obj.Label)
        obj.addProperty('App::PropertyDistance',    'Offset', 'BeamCut', QtCore.QT_TRANSLATE_NOOP('PathBeamCut', 'The desired beam offset'))
        obj.addProperty('App::PropertyBool',    'ToolComp', 'BeamCut', QtCore.QT_TRANSLATE_NOOP('PathBeamCut', 'Apply tool compensation'))
        obj.addProperty('App::PropertyDistance',    'Depth', 'BeamCut', QtCore.QT_TRANSLATE_NOOP('PathBeamCut', 'The additional depth of the tool path'))
        obj.setEditorMode('Depth', 2) # hide depth settings

    def opExecute(self, obj):
        PathLog.track(obj.Label)
        (depth, offset ) = toolOffset(obj.ToolComp, obj.Offset.Value, obj.Depth.Value, self.tool)
        PathLog.track(obj.Label, depth, offset)

        self.basewires = []
        self.adjusted_basewires = []
        wires = []
        for base, subs in obj.Base:
            edges = []
            basewires = []
            for f in subs:
                sub = base.Shape.getElement(f)
                if type(sub) == Part.Edge:
                    edges.append(sub)
                elif sub.Wires:
                    basewires.extend(sub.Wires)
                else:
                    basewires.append(Part.Wire(sub.Edges))
            self.edges = edges
            for edgelist in Part.sortEdges(edges):
                basewires.append(Part.Wire(edgelist))

            self.basewires.extend(basewires)

            for w in basewires:
                self.adjusted_basewires.append(w)
                wire = PathOpTools.offsetWire(w, base.Shape, offset, True)
	        if wire:
                    wires.append(wire)  

        zValues = []
        z = 0
        if obj.StepDown.Value != 0:
            while z + obj.StepDown.Value < depth:
                z = z + obj.StepDown.Value
                zValues.append(z)
        zValues.append(depth)
        PathLog.track(obj.Label, depth, zValues)

        self.wires = wires
        self.buildpathocc(obj, wires, zValues, True)

        # the last command is a move to clearance, which is automatically added by PathOp
        if self.commandlist:
            self.commandlist.pop()

    def opRejectAddBase(self, obj, base, sub):
        '''The Beamcut op can only deal with features of the base model, all others are rejected.'''
        return not base in self.model

    def opSetDefaultValues(self, obj, job):
        PathLog.track(obj.Label, job.Label)
        obj.Offset = '0 mm'
        obj.Depth = '0.0 mm'
        obj.setExpression('StepDown', '0 mm')
        obj.StepDown = False
 	obj.ToolComp = True

def SetupProperties():
    setup = []
    setup.append('Offset')
    setup.append('ToolComp')
    return setup

def Create(name, obj = None):
    '''Create(name) ... Creates and returns a BeamCut operation.'''
    if obj is None:
        obj = FreeCAD.ActiveDocument.addObject("Path::FeaturePython", name)
    proxy = ObjectBeamCut(obj, name)
    return obj

