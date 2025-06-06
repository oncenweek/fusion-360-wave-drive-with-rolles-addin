import os

import adsk.core
import adsk.fusion
from adsk.fusion import ConstructionPlane

from . import RollerWaveDriveBuilder as builder
from .RollerWaveDriveParams import RollerWaveDriveParams
from ... import config
from ...lib import fusionAddInUtils as futil

app = adsk.core.Application.get()
ui = app.userInterface
design = adsk.fusion.Design.cast(app.activeProduct)

CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_waveDriveDialog'
CMD_NAME = 'Wave Drive Creation Dialog'
CMD_Description = 'Create wave drive with roller elements'

IS_PROMOTED = True

# TODO *** Define the location where the command button will be created. ***
# This is done by specifying the workspace, the tab, and the panel, and the 
# command it will be inserted beside. Not providing the command to position it
# will insert it at the end.
WORKSPACE_ID = 'FusionSolidEnvironment'
PANEL_ID = 'OncenweekAddinsPanel'
COMMAND_BESIDE_ID = 'ScriptsManagerCommand'

ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', '')

local_handlers = []

ID_ROLLER_DIAMETER = 'roller_diameter'
ID_ROLLERS_NUMBER = 'rollers_number'
ID_USE_BALLS = 'use_balls'
ID_ROLLER_HEIGHT = 'roller_height'
ID_USE_MINIMAL_DIAMETER = 'use_minimal_diameter'
ID_CYCLOID_DIAMETER = 'cycloid_diameter'
ID_INPUT_SHAFT_DIAMETER = 'input_shaft_diameter'
ID_INPUT_PLANE = 'input_plane'
ID_ROLLER_TOLERANCE = 'roller_tolerance'


# Executed when add-in is run.
def start():
    # Create a command Definition.
    cmd_def = ui.commandDefinitions.addButtonDefinition(CMD_ID, CMD_NAME, CMD_Description, ICON_FOLDER)

    # Define an event handler for the command created event. It will be called when the button is clicked.
    futil.add_handler(cmd_def.commandCreated, command_created)

    # ******** Add a button into the UI so the user can run the command. ********
    # Get the target workspace the button will be created in.
    workspace = ui.workspaces.itemById(WORKSPACE_ID)

    # Get the panel the button will be created in.
    panels = workspace.toolbarPanels
    panel = panels.itemById(PANEL_ID)
    if panel:
        panel.deleteMe()
    panel = panels.add(PANEL_ID, 'ROLLER WAVE DRIVE', 'SelectPanel', False)

    # Create the button command control in the UI after the specified existing command.
    control = panel.controls.addCommand(cmd_def)

    # Specify if the command is promoted to the main toolbar. 
    control.isPromoted = IS_PROMOTED


# Executed when add-in is stopped.
def stop():
    # Get the various UI elements for this command
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    command_control = panel.controls.itemById(CMD_ID)
    command_definition = ui.commandDefinitions.itemById(CMD_ID)

    # Delete the button command control
    if command_control:
        command_control.deleteMe()

    # Delete the command definition
    if command_definition:
        command_definition.deleteMe()

    if panel:
        panel.deleteMe()


# Function that is called when a user clicks the corresponding button in the UI.
def command_created(args: adsk.core.CommandCreatedEventArgs):
    futil.log(f'{CMD_NAME} Command Created Event')

    len_units = app.activeProduct.unitsManager.defaultLengthUnits
    inputs = args.command.commandInputs

    # Define the dialog
    inputs.addImageCommandInput('image', '', 'commands/createWaveDrive/resources/diagram.png')
    inputs.addValueInput(ID_ROLLER_DIAMETER, 'Roller diameter', len_units, adsk.core.ValueInput.createByString('6'))
    inputs.addIntegerSpinnerCommandInput(ID_ROLLERS_NUMBER, 'Rollers number', 5, 100, 1, 17)
    inputs.addBoolValueInput(ID_USE_BALLS, 'Use balls', True, '', False)
    inputs.addValueInput(ID_ROLLER_HEIGHT, 'Roller height', len_units, adsk.core.ValueInput.createByString('6'))
    inputs.addBoolValueInput(ID_USE_MINIMAL_DIAMETER, 'Use minimal cycloid diameter', True, '', False)
    inputs.addValueInput(ID_CYCLOID_DIAMETER, 'Cycloid outer diameter', len_units,
                         adsk.core.ValueInput.createByString('75'))
    inputs.addValueInput(ID_INPUT_SHAFT_DIAMETER, 'Input shaft diameter', len_units,
                         adsk.core.ValueInput.createByString('5'))
    inputs.addValueInput(ID_ROLLER_TOLERANCE, 'Rollers tolerance', len_units,
                         adsk.core.ValueInput.createByString('0.1'))
    plane_select = inputs.addSelectionInput(ID_INPUT_PLANE, 'Input plane', 'tooltip')
    plane_select.addSelectionFilter(adsk.core.SelectionCommandInput.PlanarFaces)
    plane_select.addSelectionFilter(adsk.core.SelectionCommandInput.ConstructionPlanes)
    plane_select.setSelectionLimits(1, 1)

    # Connect to the events
    futil.add_handler(args.command.execute, command_execute, local_handlers=local_handlers)
    futil.add_handler(args.command.inputChanged, command_input_changed, local_handlers=local_handlers)
    futil.add_handler(args.command.validateInputs, command_validate_input, local_handlers=local_handlers)
    futil.add_handler(args.command.destroy, command_destroy, local_handlers=local_handlers)


# This event handler is called when the user clicks the OK button in the command dialog or 
# is immediately called after the created event not command inputs were created for the dialog.
def command_execute(args: adsk.core.CommandEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME} Command Execute Event')

    inputs = args.command.commandInputs
    params = get_params_from_inputs(inputs)
    plane_input: adsk.core.SelectionCommandInput = inputs.itemById(ID_INPUT_PLANE)

    root = design.rootComponent
    plane: ConstructionPlane = plane_input.selection(0).entity

    component = root.occurrences.addNewComponent(adsk.core.Matrix3D.create()).component
    component.name = 'RollerWaveDrive-1-to-{}'.format(params.roller_number)

    builder.draw_gear(params, component, plane)
    builder.draw_separator(params, component, plane)
    builder.draw_cam(params, component, plane)
    builder.draw_rollers(params, component, plane)


# This event handler is called when the user changes anything in the command dialog
# allowing you to modify values of other inputs based on that change.
def command_input_changed(args: adsk.core.InputChangedEventArgs):
    changed_input = args.input
    inputs = args.inputs
    if changed_input.id == ID_USE_BALLS:
        use_balls_input: adsk.core.BoolValueCommandInput = inputs.itemById(ID_USE_BALLS)
        roller_height_input: adsk.core.ValueCommandInput = inputs.itemById(ID_ROLLER_HEIGHT)
        roller_height_input.isEnabled = not use_balls_input.value

    if changed_input.id == ID_USE_MINIMAL_DIAMETER:
        use_minimal_diameter_input: adsk.core.BoolValueCommandInput = inputs.itemById(ID_USE_MINIMAL_DIAMETER)
        cycloid_diameter_input: adsk.core.ValueCommandInput = inputs.itemById(ID_CYCLOID_DIAMETER)
        use_minimal_diameter = use_minimal_diameter_input.value
        cycloid_diameter_input.isEnabled = not use_minimal_diameter
        if use_minimal_diameter:
            cycloid_diameter_input.value = get_params_from_inputs(inputs).min_cycloid_radius * 2

    # General logging for debug.
    futil.log(f'{CMD_NAME} Input Changed Event fired from a change to {changed_input.id}')


# This event handler is called when the user interacts with any of the inputs in the dialog
# which allows you to verify that all of the inputs are valid and enables the OK button.
def command_validate_input(args: adsk.core.ValidateInputsEventArgs):
    futil.log(f'{CMD_NAME} Validate Input Event')
    inputs = args.inputs
    params = get_params_from_inputs(inputs)
    if params.internal_radius < params.min_cycloid_radius:
        args.areInputsValid = False
        return
    args.areInputsValid = True


# This event handler is called when the command terminates.
def command_destroy(args: adsk.core.CommandEventArgs):
    futil.log(f'{CMD_NAME} Command Destroy Event')
    global local_handlers
    local_handlers = []


def get_params_from_inputs(inputs: adsk.core.CommandInputs) -> RollerWaveDriveParams:
    roller_diameter_input: adsk.core.ValueCommandInput = inputs.itemById(ID_ROLLER_DIAMETER)
    rollers_number_input: adsk.core.IntegerSpinnerCommandInput = inputs.itemById(ID_ROLLERS_NUMBER)
    use_balls_input: adsk.core.BoolValueCommandInput = inputs.itemById(ID_USE_BALLS)
    roller_height_input: adsk.core.ValueCommandInput = inputs.itemById(ID_ROLLER_HEIGHT)
    use_minimal_diameter_input: adsk.core.BoolValueCommandInput = inputs.itemById(ID_USE_MINIMAL_DIAMETER)
    cycloid_diameter_input: adsk.core.ValueCommandInput = inputs.itemById(ID_CYCLOID_DIAMETER)
    shaft_diameter_input: adsk.core.ValueCommandInput = inputs.itemById(ID_INPUT_SHAFT_DIAMETER)
    rollers_tolerance_input: adsk.core.ValueCommandInput = inputs.itemById(ID_ROLLER_TOLERANCE)

    return RollerWaveDriveParams(
        roller_diameter_input.value,
        rollers_number_input.value,
        use_balls_input.value,
        roller_height_input.value,
        use_minimal_diameter_input.value,
        cycloid_diameter_input.value,
        shaft_diameter_input.value,
        rollers_tolerance_input.value
    )
