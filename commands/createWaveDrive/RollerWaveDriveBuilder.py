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
    profile_sketch.name = 'Wheel'
    points = adsk.core.ObjectCollection.create()

    for i in range(params.resolution):
        theta = math.pi * 2.0 * i / params.resolution
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
                                                                params.body_diameter)

    extrudes = component.features.extrudeFeatures
    prof = profile_sketch.profiles.item(0)
    distance = adsk.core.ValueInput.createByReal(get_extrusion_height(params))
    disk_extrude = extrudes.addSimple(prof, distance, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    disk_extrude.bodies.item(0).name = "CycloidWheel"


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
    hole_feature = create_round_hole(params, component, plane) if params.use_balls else create_square_hole(params,
                                                                                                           component,
                                                                                                           plane)
    create_circular_pattern(axis, hole_feature, params.roller_number)


def create_round_hole(params: RollerWaveDriveParams, component: Component, plane: ConstructionPlane) -> Feature:
    extrudes = component.features.extrudeFeatures
    planes = component.constructionPlanes
    plane_input = planes.createInput()
    plane_input.setByOffset(plane, adsk.core.ValueInput.createByReal(0.1 + params.roller_height / 2))
    holes_plane = planes.add(plane_input)
    holes_sketch = component.sketches.add(holes_plane)
    holes_sketch.name = 'RollerHole'
    r = params.roller_diameter / 2 + params.roller_tolerance

    holes_sketch.sketchCurves.sketchCircles.addByThreePoints(
        adsk.core.Point3D.create(0, params.separator_outer_radius, -r),
        adsk.core.Point3D.create(r, params.separator_outer_radius, 0),
        adsk.core.Point3D.create(0, params.separator_outer_radius, r),
    )

    prof = holes_sketch.profiles.item(0)
    distance = adsk.core.ValueInput.createByReal(params.separator_thickness * 2)
    hole_extrude = extrudes.addSimple(prof, distance, adsk.fusion.FeatureOperations.CutFeatureOperation)
    return hole_extrude


def create_square_hole(params: RollerWaveDriveParams, component: Component, plane: ConstructionPlane) -> Feature:
    extrudes = component.features.extrudeFeatures
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
    return hole_extrude


def create_circular_pattern(axis: ConstructionAxis, feature: Feature, num_copies: int):
    collection = adsk.core.ObjectCollection.create()
    collection.add(feature)
    pattern_features = feature.parentComponent.features.circularPatternFeatures
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


def draw_balls(params: RollerWaveDriveParams, component: Component, plane: ConstructionPlane):
    num_dimples = params.roller_number + 1
    ball_radius = params.roller_diameter / 2

    revolves = component.features.revolveFeatures
    planes = component.constructionPlanes
    plane_input = planes.createInput()
    plane_input.setByOffset(plane, adsk.core.ValueInput.createByReal(0.1 + params.roller_height / 2))
    plane = planes.add(plane_input)

    for i in range(0, params.roller_number):
        angle = 2 * math.pi * i / params.roller_number
        s_sh = math.sqrt(
            (ball_radius + params.cam_radius) ** 2 - math.pow(params.eccentricity * math.sin(num_dimples * angle), 2))
        l_sh = params.eccentricity * math.cos(num_dimples * angle) + s_sh
        x = l_sh * math.sin(angle)
        y = l_sh * math.cos(angle)

        sketch = component.sketches.add(plane)
        sketch.name = "Ball-{}".format(i)
        sketch.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(x, y, 0),
                                                            params.roller_diameter / 2)

        axis = sketch.sketchCurves.sketchLines.addByTwoPoints(
            adsk.core.Point3D.create(x, y - params.roller_diameter, 0),
            adsk.core.Point3D.create(x, y + params.roller_diameter, 0)
        )
        axis.isCenterLine = True

        ball_input = revolves.createInput(sketch.profiles.item(0), axis,
                                          adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        ball_input.setAngleExtent(False, adsk.core.ValueInput.createByReal(2 * math.pi))
        feat = revolves.add(ball_input)
        feat.name = sketch.name


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
    rollers = extrudes.add(extrude_input)
    rollers.name = "Roller-"


def draw_cam(params: RollerWaveDriveParams, component: Component, plane: ConstructionPlane):
    sketch = component.sketches.add(plane)
    sketch.name = 'Cam'
    sketch.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(0, 0, 0),
                                                        params.shaft_diameter / 2)
    sketch.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(0, params.eccentricity, 0),
                                                        params.cam_radius)

    extrudes = component.features.extrudeFeatures
    prof = sketch.profiles.item(1)
    distance = adsk.core.ValueInput.createByReal(get_extrusion_height(params))
    cam_extrude = extrudes.addSimple(prof, distance, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    cam_extrude.bodies.item(0).name = "Cam"

    sketch = component.sketches.add(plane)
    sketch.name = 'CamSplit'
    sketch.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(0, params.eccentricity, 0),
                                                        params.bearing_middle_diameter / 2 + 0.1)
    sketch.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(0, params.eccentricity, 0),
                                                        params.bearing_middle_diameter / 2 - 0.1)
    prof = sketch.profiles.item(0)
    distance = adsk.core.ValueInput.createByReal(get_extrusion_height(params))
    extrudes.addSimple(prof, distance, adsk.fusion.FeatureOperations.CutFeatureOperation)

    sketch = component.sketches.add(plane)
    sketch.name = 'Bearing'
    sketch.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(0, params.eccentricity, 0),
                                                        params.bearing_outer_diameter / 2)
    sketch.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(0, params.eccentricity, 0),
                                                        params.bearing_inner_diameter / 2)
    prof = sketch.profiles.item(0)
    distance = adsk.core.ValueInput.createByReal(params.bearing_height)
    extrudes.addSimple(prof, distance, adsk.fusion.FeatureOperations.CutFeatureOperation)
