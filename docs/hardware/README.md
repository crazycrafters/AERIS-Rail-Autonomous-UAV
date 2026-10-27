# Hardware learning pack

Read these in order:

1. [Student build manual](student_build_manual.md): assemble a supported kit, understand the boards, connect parts, map motors and commission the baseline aircraft.
2. [Hardware selection and connections](../uav_hardware_and_connections.md): choose computer, camera, lens, OS, power and interfaces from measured requirements.
3. [Custom airframe/controller design](custom_airframe_and_controller.md): the engineering and validation steps needed if you want to manufacture those components yourself.
4. [Software implementation guide](../implementation_guide.md): train `best.pt`, run inference, replay evidence and prepare SITL.

## Printable copies

The repository includes `student_build_manual.html` and `custom_airframe_and_controller.html`. After cloning/pulling the repository, open either file directly in a browser, then choose **Print → Save as PDF**. The student HTML embeds all four SVG diagrams, so reading/printing the figures does not require an image server. Other manuals/worksheets are linked separately.

GitHub usually shows HTML source instead of rendering it as a website. Use the Markdown links above when reading on GitHub; open the downloaded HTML locally for print layout.

## Visual assets

- [Whole-system power/data diagram](assets/01_system_wiring.svg)
- [Physical aircraft layout](assets/02_airframe_layout.svg)
- [Flight-controller logical board functions](assets/03_controller_functions.svg)
- [USB/UART companion-link diagram](assets/04_companion_link.svg)

These are conceptual engineering illustrations. They are not manufacturing drawings or pin-number charts for a purchased board.

## Fill-in worksheets

- [Parts and compatibility BOM](../../examples/hardware/prototype_bom.csv)
- [Wire-by-wire connection schedule](../../examples/hardware/wire_schedule.csv)
- [Motor/output/rotation mapping](../../examples/hardware/motor_map.csv)
- [Power and mass measurements](../../examples/hardware/power_and_mass.csv)
- [Assembly and commissioning checklist](../../examples/hardware/assembly_checklist.csv)

Open the CSVs in a spreadsheet and save project-specific copies in your build records. A blank worksheet is not a completed design or passed inspection.

## Updating the printable manuals

If editing the Markdown or SVG sources, regenerate the HTML with the optional authoring dependency:

```sh
python -m pip install -r requirements-docs.txt
python scripts/build_hardware_manual.py
python scripts/build_hardware_manual.py --check
```

Run those commands from the repository root. Readers do not need Python/Markdown to open the checked-in HTML.
