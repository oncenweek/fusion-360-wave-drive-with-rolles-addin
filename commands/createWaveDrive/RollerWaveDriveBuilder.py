import math

import adsk.core
import adsk.fusion
from adsk.fusion import Component
from adsk.fusion import ConstructionPlane, BRepBody, BRepFace, ConstructionAxis, Feature

from .RollerWaveDriveParams import RollerWaveDriveParams


def get_extrusion_height(params: RollerWaveDriveParams) -> float:
    return params.roller_height + 2 * params.roller_tolerance + 0.2


def find_cylindrical_face(body: BRepBody) -> BRepFace:
    for face in body.faces:
        geom = face.geometry
        if geom.surfaceType == adsk.core.SurfaceTypes.CylinderSurfaceType:
            return face


def draw_gear(params: RollerWaveDriveParams, component: Component, plane: ConstructionPlane):
    num_dimples = params.roller_number + 1
    ball_radius = params.roller_diameter / 2
    eccentricity = params.eccentricity

    profile_sketch = component.sketches.add(plane)
    profile_sketch.name = 'Disk'
    points = adsk.core.ObjectCollection.create()

    for i in range(params.RESOLUTION):
        theta = math.pi * 2.0 * i / params.RESOLUTION
        S = math.sqrt(
            (ball_radius + params.cam_radius) ** 2 - math.pow(eccentricity * math.sin(num_dimples * theta), 2))
        l = eccentricity * math.cos(num_dimples * theta) + S
        xi = math.atan2(eccentricity * num_dimples * math.sin(num_dimples * theta), S)

        x = l * math.sin(theta) + ball_radius * math.sin(theta + xi)
        y = l * math.cos(theta) + ball_radius * math.cos(theta + xi)

        point = adsk.core.Point3D.create(x, y, 0)
        points.add(point)
    points.add(points[0])

    profile_spline = profile_sketch.sketchCurves.sketchFittedSplines.add(points)
    profile_spline.isClosed = True

    profile_sketch.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(0, 0, 0),
                                                                params.cycloid_diameter + 0.2)

    extrudes = component.features.extrudeFeatures
    prof = profile_sketch.profiles.item(0)
    distance = adsk.core.ValueInput.createByReal(get_extrusion_height(params))
    disk_extrude = extrudes.addSimple(prof, distance, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    disk_extrude.bodies.item(0).name = "CycloidDisk"


def draw_separator(params: RollerWaveDriveParams, component: Component, plane: ConstructionPlane):
    sketch = component.sketches.add(plane)
    sketch.name = 'Separator'
    sketch.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(0, 0, 0),
                                                        params.separator_inner_radius)
    sketch.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(0, 0, 0),
                                                        params.separator_outer_radius)

    extrudes = component.features.extrudeFeatures
    prof = sketch.profiles.item(1)
    distance = adsk.core.ValueInput.createByReal(get_extrusion_height(params))
    separator_extrude = extrudes.addSimple(prof, distance, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    separator_body = separator_extrude.bodies.item(0)
    separator_body.name = "Separator"

    axis = create_axis_from_cylindrical_body(component, separator_body)

    planes = component.constructionPlanes
    plane_input = planes.createInput()
    plane_input.setByOffset(plane, adsk.core.ValueInput.createByReal(0.1))
    holes_plane = planes.add(plane_input)

    holes_sketch = component.sketches.add(holes_plane)
    holes_sketch.name = 'RollerHole'
    holes_sketch.sketchCurves.sketchLines.addCenterPointRectangle(
        adsk.core.Point3D.create(0, params.separator_middle_radius, 0),
        adsk.core.Point3D.create(params.roller_diameter / 2 + params.roller_tolerance,
                                 params.separator_middle_radius + params.separator_thickness, 0),
    )

    prof = holes_sketch.profiles.item(0)
    distance = adsk.core.ValueInput.createByReal(params.roller_height + 2 * params.roller_tolerance)
    hole_extrude = extrudes.addSimple(prof, distance, adsk.fusion.FeatureOperations.CutFeatureOperation)

    create_circular_pattern(axis, hole_extrude, params.roller_number)


def create_circular_pattern(axis: ConstructionAxis, hole_extrude: Feature, num_copies: int):
    collection = adsk.core.ObjectCollection.create()
    collection.add(hole_extrude)
    pattern_features = hole_extrude.parentComponent.features.circularPatternFeatures
    pattern_input = pattern_features.createInput(collection, axis)
    pattern_input.quantity = adsk.core.ValueInput.createByReal(num_copies)
    pattern_input.totalAngle = adsk.core.ValueInput.createByString('360 deg')
    pattern_input.isSymmetric = False
    pattern_features.add(pattern_input)


def create_axis_from_cylindrical_body(component: Component, separator_body: BRepBody) -> ConstructionAxis:
    axis_input = component.constructionAxes.createInput()
    axis_input.setByCircularFace(find_cylindrical_face(separator_body))
    axis = component.constructionAxes.add(axis_input)
    return axis


def draw_rollers(params: RollerWaveDriveParams, component: Component, plane: ConstructionPlane):
    num_dimples = params.roller_number + 1
    ball_radius = params.roller_diameter / 2

    planes = component.constructionPlanes
    plane_input = planes.createInput()
    plane_input.setByOffset(plane, adsk.core.ValueInput.createByReal(0.1 + params.roller_tolerance))
    plane = planes.add(plane_input)

    sketch = component.sketches.add(plane)
    sketch.name = 'Rollers'

    for i in range(0, params.roller_number):
        angle = 2 * math.pi * i / params.roller_number
        s_sh = math.sqrt(
            (ball_radius + params.cam_radius) ** 2 - math.pow(params.eccentricity * math.sin(num_dimples * angle), 2))
        l_sh = params.eccentricity * math.cos(num_dimples * angle) + s_sh
        x = l_sh * math.sin(angle)
        y = l_sh * math.cos(angle)

        sketch.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(x, y, 0),
                                                            params.roller_diameter / 2)

    extrudes = component.features.extrudeFeatures
    collection = adsk.core.ObjectCollection.create()
    for i in range(0, params.roller_number):
        collection.add(sketch.profiles.item(i))
    distance = adsk.core.ValueInput.createByReal(params.roller_height)
    extrude_input = extrudes.createInput(collection, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    extrude_input.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(distance),
                                   adsk.fusion.ExtentDirections.PositiveExtentDirection)
    extrudes.add(extrude_input)


def draw_cam(params: RollerWaveDriveParams, component: Component, plane: ConstructionPlane):
    sketch = component.sketches.add(plane)
    sketch.name = 'Cam'
    sketch.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(0, 0, 0), params.shaft_diameter)
    sketch.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(0, params.eccentricity, 0),
                                                        params.cam_radius)

    extrudes = component.features.extrudeFeatures
    prof = sketch.profiles.item(1)
    distance = adsk.core.ValueInput.createByReal(get_extrusion_height(params))
    disk_extrude = extrudes.addSimple(prof, distance, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    disk_extrude.bodies.item(0).name = "Cam"
